import pickle

import osu

from misc.osuvs_constants import *
from misc.osuvs_utils import *

SECRETS_DIR: str = "./secrets"

try:
    with open(f"{SECRETS_DIR}/osu_api.pickle", "rb") as f:
        OSU_API_DETAILS: dict[str, str | int] = pickle.load(f)
        assert isinstance(OSU_API_DETAILS["client_id"], int)
        assert isinstance(OSU_API_DETAILS["client_secret"], str)
except FileNotFoundError:
    print("osu! API details file not found.")
    exit(1)


class CachedOsuClient:
    _client: osu.Client
    users: TTLCachedDict[tuple[OsuUserId, osu.GameModeStr], osu.User]
    beatmaps: TTLCachedDict[OsuBeatmapId, osu.Beatmap]

    def __init__(self, client: osu.Client):
        self._client = client
        self.users = TTLCachedDict(
            maxsize=1000,
            ttl=60,
            get_func=lambda x: self._client.get_user(int(x[0]), mode=x[1], key="id"),
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
