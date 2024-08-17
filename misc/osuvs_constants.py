from enum import Enum
from typing import Literal, overload

from osu import GameModeStr


class DiscordUserId(int):
    """Represents a Discord user ID"""

    pass


class OsuUserId(int):
    """Represents an osu! user ID"""

    pass


class OsuBeatmapId(int):
    """Represents an osu! beatmap ID"""

    pass


class IdType(Enum):
    discord_id = "discord_id"
    osu_id = "osu_id"


class RatingDataType(Enum):
    mu = "mu"
    sigma = "sigma"


class RatingModelType(Enum):
    osu = "osu"
    taiko = "taiko"
    fruits = "fruits"
    mania = "mania"

    def __init__(
        self, modestr: GameModeStr | Literal["osu", "taiko", "fruits", "mania"]
    ) -> None:
        match modestr:
            case GameModeStr.STANDARD | "osu":
                self = "osu"
            case GameModeStr.TAIKO | "taiko":
                self = "taiko"
            case GameModeStr.CATCH | "fruits":
                self = "fruits"
            case GameModeStr.MANIA | "mania":
                self = "mania"
