import logging
import pickle
import re
from typing import Callable, Mapping, Never, TypeVar

import osu
from cachetools import TTLCache

from misc.constants import OsuBeatmapId, OsuUserId

logger = logging.getLogger("osuvs." + __name__)
logger.setLevel(logging.DEBUG)

_SECRETS_DIR: str = "./secrets"

try:
    with open(f"{_SECRETS_DIR}/osu_api.pickle", "rb") as f:
        _OSU_API_DETAILS: dict[str, str | int] = pickle.load(f)
        assert isinstance(_OSU_API_DETAILS["client_id"], int)
        assert isinstance(_OSU_API_DETAILS["client_secret"], str)
except FileNotFoundError as e:
    raise RuntimeError("osu! API details file not found.") from e


def parse_beatmap_url(url: str) -> tuple[int, osu.GameModeStr, int]:
    logger.debug(f"Parsing beatmap URL: {url}")
    re_match = re.search(
        r"/beatmapsets/(?P<set_id>\d+)#(?P<mode>[a-z]+)/(?P<diff_id>\d+)", url
    )
    if not re_match:
        raise ValueError("Invalid URL.")
    set_id: int = int(re_match.group("set_id"))
    modestr: str = re_match.group("mode")
    match modestr:
        case "osu":
            mode = osu.GameModeStr.STANDARD
        case "taiko":
            mode = osu.GameModeStr.TAIKO
        case "fruits":
            mode = osu.GameModeStr.CATCH
        case "mania":
            mode = osu.GameModeStr.MANIA
        case _:
            raise ValueError(
                "Invalid mode. Must be one of 'osu', 'taiko', 'fruits', 'mania'."
            )
    diff_id: int = int(re_match.group("diff_id"))
    logger.debug(f"Parsed beatmap details: {set_id}, {modestr}, {diff_id}")
    return (set_id, mode, diff_id)


_K, _V = TypeVar("K"), TypeVar("V")


class _TTLCachedDict(Mapping[_K, _V]):
    _log: logging.Logger
    _cache: TTLCache[_K, _V]
    _get_func: Callable[[_K], _V]

    def __init__(self, maxsize: int, ttl: int, get_func: Callable[[_K], _V]) -> None:
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._get_func = get_func
        self._log = logging.getLogger(
            logger.name + ".client." + self.__class__.__name__
        )

    def __getitem__(self, key: _K) -> _V:
        if key not in self._cache:
            self._log.debug(f"Cache miss for key {key}")
            try:
                self._cache[key] = self._get_func(key)
            except Exception as e:
                raise KeyError("Failed to retrieve value.") from e
        else:
            self._log.debug(f"Cache hit for key {key}")
        return self._cache[key]

    def __contains__(self, key: _K) -> bool:
        self._log.debug(f"Checking availability of key {key}")
        try:
            _ = self.get(key)
            return True
        except KeyError:
            return False

    def __iter__(self) -> Never:
        self._log.error(f"Cannot iterate over api queries")
        raise NotImplementedError

    def __len__(self) -> Never:
        self._log.error(f"Cannot get length of api queries")
        raise NotImplementedError


class _CachedOsuClient:
    _client: osu.Client
    _log: logging.Logger
    users: _TTLCachedDict[tuple[OsuUserId | str, osu.GameModeStr | None], osu.User]
    beatmaps: _TTLCachedDict[OsuBeatmapId, osu.Beatmap]

    def _get_user(self, user_id: OsuUserId | str, mode: osu.GameModeStr | None):
        if mode:
            return self._client.get_user(
                int(user_id) if isinstance(user_id, OsuUserId) else user_id,  # type: ignore
                mode,
                key=("id" if isinstance(user_id, OsuUserId | int) else "username"),
            )
        else:
            return self._client.get_user(
                int(user_id) if isinstance(user_id, OsuUserId) else user_id,  # type: ignore
                key=("id" if isinstance(user_id, OsuUserId | int) else "username"),
            )

    def __init__(self, osu_client: osu.Client):
        self._client = osu_client
        self.users = _TTLCachedDict(
            maxsize=1000,
            ttl=60,
            get_func=lambda x: self._get_user(x[0], x[1]),
        )
        self.beatmaps = _TTLCachedDict(
            maxsize=1000,
            ttl=60 * 15,
            get_func=lambda x: self._client.get_beatmap(int(x)),
        )
        self._log = logging.getLogger(logger.name + ".client")
        self._log.debug("Initialized cached osu! client")


client = _CachedOsuClient(
    osu.Client.from_credentials(
        _OSU_API_DETAILS["client_id"], _OSU_API_DETAILS["client_secret"], None
    )
)

logger.info("osu! API client initialized successfully.")
