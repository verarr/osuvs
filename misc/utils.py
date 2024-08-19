from typing import Callable, Mapping, Never, TypeVar

from cachetools import TTLCache

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
            except Exception as e:
                raise KeyError("Failed to retrieve value.") from e
        return self._cache[key]

    def __contains__(self, key: K) -> bool:
        try:
            _ = self.get(key)
            return True
        except KeyError:
            return False

    def __iter__(self) -> Never:
        raise NotImplementedError

    def __len__(self) -> Never:
        raise NotImplementedError
