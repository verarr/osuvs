import pickle

import osu

from .misc.osuvs_constants import OsuBeatmapId, OsuUserId
from .misc.osuvs_utils import TTLCachedDict

SECRETS_DIR: str = "./secrets"

try:
    with open(f"{SECRETS_DIR}/osu_api.pickle", "rb") as f:
        OSU_API_DETAILS: dict[str, str | int] = pickle.load(f)
        assert isinstance(OSU_API_DETAILS["client_id"], int)
        assert isinstance(OSU_API_DETAILS["client_secret"], str)
except FileNotFoundError as e:
    raise RuntimeError("osu! API details file not found.") from e


class CachedOsuClient:
    _client: osu.Client
    users: TTLCachedDict[tuple[OsuUserId | str, osu.GameModeStr | None], osu.User]
    beatmaps: TTLCachedDict[OsuBeatmapId, osu.Beatmap]

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
        self.users = TTLCachedDict(
            maxsize=1000,
            ttl=60,
            get_func=lambda x: self._get_user(x[0], x[1]),
        )
        self.beatmaps = TTLCachedDict(
            maxsize=1000,
            ttl=60 * 15,
            get_func=lambda x: self._client.get_beatmap(int(x)),
        )


client = CachedOsuClient(
    osu.Client.from_credentials(
        OSU_API_DETAILS["client_id"], OSU_API_DETAILS["client_secret"], None
    )
)
