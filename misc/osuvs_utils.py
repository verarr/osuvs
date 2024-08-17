import re
from typing import Callable, Mapping, Never, TypeVar

from cachetools import TTLCache
from osu import GameModeStr


def parse_beatmap_url(url: str) -> tuple[int, GameModeStr, int]:
    re_match = re.search(
        r"/beatmapsets/(?P<set_id>\d+)#(?P<mode>[a-z]+)/(?P<diff_id>\d+)", url
    )
    if not re_match:
        raise ValueError("Invalid URL.")
    set_id: int = int(re_match.group("set_id"))
    modestr: str = re_match.group("mode")
    match modestr:
        case "osu":
            mode = GameModeStr.STANDARD
        case "taiko":
            mode = GameModeStr.TAIKO
        case "fruits":
            mode = GameModeStr.CATCH
        case "mania":
            mode = GameModeStr.MANIA
        case _:
            raise ValueError(
                "Invalid mode. Must be one of 'osu', 'taiko', 'fruits', 'mania'."
            )
    diff_id: int = int(re_match.group("diff_id"))
    return (set_id, mode, diff_id)


K, V = TypeVar("K"), TypeVar("V")


class TTLCachedDict(Mapping[K, V]):
    _cache: TTLCache[K, V]
    _get_func: Callable[[K], V]

    def __init__(self, maxsize: int, ttl: int, get_func: Callable[[K], V]) -> None:
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._get_func = get_func

    def __getitem__(self, key: K) -> V:
        if key not in self._cache:
            try:
                self._cache[key] = self._get_func(key)
            except:
                raise KeyError("Failed to retrieve value.")
        return self._cache[key]

    def __contains__(self, key: K) -> bool:
        try:
            _ = self.get(key)
            return True
        except:
            return False

    def __iter__(self) -> Never:
        raise NotImplementedError

    def __len__(self) -> Never:
        raise NotImplementedError


from abc import ABCMeta, abstractmethod
from typing import Any, TypeVar


class ComparableAddable(metaclass=ABCMeta):
    @abstractmethod
    def __lt__(self, other: Any) -> bool: ...
    @abstractmethod
    def __add__(self, other: Any) -> Any: ...
    @abstractmethod
    def __sub__(self, other: Any) -> Any: ...


CTA = TypeVar("CTA", bound=ComparableAddable)
