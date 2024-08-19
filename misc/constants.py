from enum import Enum
from typing import Literal

from osu import GameModeStr


class DiscordUserId(int):
    """Represents a Discord user ID"""


class OsuUserId(int):
    """Represents an osu! user ID"""


class OsuBeatmapId(int):
    """Represents an osu! beatmap ID"""


class IdType(Enum):
    DISCORD_ID = "discord_id"
    OSU_ID = "osu_id"


class RatingDataType(Enum):
    MU = "mu"
    SIGMA = "sigma"


class RatingModelType(Enum):
    OSU = "osu"
    TAIKO = "taiko"
    FRUITS = "fruits"
    MANIA = "mania"

    @classmethod
    def from_gamemodestr(
        cls, modestr: GameModeStr | Literal["osu", "taiko", "fruits", "mania"]
    ) -> "RatingModelType":
        match modestr:
            case GameModeStr.STANDARD | "osu":
                return cls.OSU
            case GameModeStr.TAIKO | "taiko":
                return cls.TAIKO
            case GameModeStr.CATCH | "fruits":
                return cls.FRUITS
            case GameModeStr.MANIA | "mania":
                return cls.MANIA
