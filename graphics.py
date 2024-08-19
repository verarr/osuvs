import dataclasses
import subprocess
from datetime import datetime
from typing import Callable, Literal

import pytz
from openskill.models.weng_lin.plackett_luce import PlackettLuceRating
from osu import User
from unopt import unwrap

import ratings as ratings


def _elo_function(player: PlackettLuceRating):
    return player.ordinal(alpha=200 / player.sigma, target=1500)


def _change(
    before: Callable[[], int | float] | int | float,
    after: Callable[[], int | float] | int | float,
    formatter: Callable[[int | float], str],
    position: Literal["before", "after"],
) -> tuple[str, str]:

    if isinstance(before, Callable):
        before = before()
    if isinstance(after, Callable):
        after = after()

    increase = ""
    if after > before:
        increase = (
            ("▲ " if position == "before" else "")
            + formatter(after - before)
            + (" ▲" if position == "after" else "")
        )

    decrease = ""
    if before > after:
        decrease = (
            ("▼ " if position == "before" else "")
            + formatter(before - after)
            + (" ▼" if position == "after" else "")
        )

    return (increase, decrease)


def integer(x):
    return str(int(round(x, 0)))


def long_integer(x):
    return "{:,}".format(int(round(x, 0)))


def short_decimal(x):
    return str(round(x, 2))


def percentage(x):
    return integer(x * 100)


@dataclasses.dataclass
class _Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height


GRAPHICS = "./graphics"
INKSCAPE = "/usr/bin/inkscape"

BANNER_SIZE: _Rectangle = _Rectangle(1100, 650)
SMALL_PROFILE_SIZE: _Rectangle = _Rectangle(1100, 405)

_UTC = pytz.timezone("UTC")


class Graphic:
    def render(self) -> tuple[dict[str, str], str, _Rectangle]: ...


class OneVOneBeforeGraphic(Graphic):
    player1: tuple[User, PlackettLuceRating]
    player2: tuple[User, PlackettLuceRating]
    model: ratings.RatingModel

    def __init__(
        self,
        player1: tuple[User, PlackettLuceRating],
        player2: tuple[User, PlackettLuceRating],
        model: ratings.RatingModel,
    ):
        self.player1 = player1
        self.player2 = player2
        self.model = model

    def render(self) -> tuple[dict[str, str], str, _Rectangle]:
        chances = self.model.model.predict_win([[self.player1[1]], [self.player2[1]]])
        return (
            {
                "PREDICTION_METER_STOP_1": str(chances[0] - 0.005),
                "PREDICTION_METER_STOP_2": str(chances[0] - 0.005),
                "PREDICTION_METER_STOP_3": str(chances[0] + 0.005),
                "PREDICTION_METER_STOP_4": str(chances[0] + 0.005),
                "PLAYER1_COVER_URL": self.player1[0].cover_url,
                "PLAYER2_COVER_URL": self.player2[0].cover_url,
                "PLAYER1_AVATAR_URL": self.player1[0].avatar_url,
                "PLAYER2_AVATAR_URL": self.player2[0].avatar_url,
                "PLAYER1_NAME": self.player1[0].username,
                "PLAYER2_NAME": self.player2[0].username,
                "PLAYER1_RANK": long_integer(
                    unwrap(unwrap(self.player1[0].statistics).global_rank)
                ),
                "PLAYER2_RANK": long_integer(
                    unwrap(unwrap(self.player2[0].statistics).global_rank)
                ),
                "PLAYER1_PP": integer(unwrap(unwrap(self.player1[0].statistics).pp)),
                "PLAYER2_PP": integer(unwrap(unwrap(self.player2[0].statistics).pp)),
                "PLAYER1_COUNTRY": self.player1[0].country_code,
                "PLAYER2_COUNTRY": self.player2[0].country_code,
                "PLAYER1_CHANCE": percentage(chances[0]),
                "PLAYER2_CHANCE": percentage(chances[1]),
                "PLAYER1_ELO": integer(_elo_function(self.player1[1])),
                "PLAYER2_ELO": integer(_elo_function(self.player2[1])),
                "PLAYER1_MU": short_decimal(self.player1[1].mu),
                "PLAYER2_MU": short_decimal(self.player2[1].mu),
                "PLAYER1_SIGMA": short_decimal(self.player1[1].sigma),
                "PLAYER2_SIGMA": short_decimal(self.player2[1].sigma),
                "MATCH_DATE": datetime.now(_UTC).strftime("%A %d %B %Y %H:%M %Z"),
                "RATING_MODEL": self.model.model_type.value,
            },
            f"{GRAPHICS}/1v1-before.svg",
            BANNER_SIZE,
        )


class OneVOneAfterGraphic(Graphic):
    player1: tuple[User, tuple[PlackettLuceRating, PlackettLuceRating], int]
    player2: tuple[User, tuple[PlackettLuceRating, PlackettLuceRating], int]
    model: ratings.RatingModel
    winner: Literal["player1", "player2"]
    watermark: str

    def __init__(
        self,
        player1: tuple[User, tuple[PlackettLuceRating, PlackettLuceRating], int],
        player2: tuple[User, tuple[PlackettLuceRating, PlackettLuceRating], int],
        model: ratings.RatingModel,
        winner: Literal["player1", "player2"] = "player1",
        watermark: str = "",
    ):
        self.player1 = player1
        self.player2 = player2
        self.model = model
        self.winner = winner
        self.watermark = watermark

    def render(self) -> tuple[dict[str, str], str, _Rectangle]:
        return (
            {
                "PLAYER1_COVER_URL": self.player1[0].cover_url,
                "PLAYER2_COVER_URL": self.player2[0].cover_url,
                "PLAYER1_AVATAR_URL": self.player1[0].avatar_url,
                "PLAYER2_AVATAR_URL": self.player2[0].avatar_url,
                "PLAYER1_NAME_WINNER": (
                    self.player1[0].username if self.winner == "player1" else ""
                ),
                "PLAYER1_NAME_LOSER": (
                    self.player1[0].username if self.winner == "player2" else ""
                ),
                "PLAYER2_NAME_WINNER": (
                    self.player2[0].username if self.winner == "player2" else ""
                ),
                "PLAYER2_NAME_LOSER": (
                    self.player2[0].username if self.winner == "player1" else ""
                ),
                "PLAYER1_RANK": long_integer(
                    unwrap(unwrap(self.player1[0].statistics).global_rank)
                ),
                "PLAYER2_RANK": long_integer(
                    unwrap(unwrap(self.player2[0].statistics).global_rank)
                ),
                "PLAYER1_PP": integer(unwrap(unwrap(self.player1[0].statistics).pp)),
                "PLAYER2_PP": integer(unwrap(unwrap(self.player2[0].statistics).pp)),
                "PLAYER1_COUNTRY": self.player1[0].country_code,
                "PLAYER2_COUNTRY": self.player2[0].country_code,
                "PLAYER1_ELO_INCREASE": _change(
                    lambda: _elo_function(self.player1[1][0]),
                    lambda: _elo_function(self.player1[1][1]),
                    integer,
                    "after",
                )[0],
                "PLAYER1_ELO_DECREASE": _change(
                    lambda: _elo_function(self.player1[1][0]),
                    lambda: _elo_function(self.player1[1][1]),
                    integer,
                    "after",
                )[1],
                "PLAYER1_ELO": integer(_elo_function(self.player1[1][1])),
                "PLAYER2_ELO_INCREASE": _change(
                    lambda: _elo_function(self.player2[1][0]),
                    lambda: _elo_function(self.player2[1][1]),
                    integer,
                    "after",
                )[0],
                "PLAYER2_ELO_DECREASE": _change(
                    lambda: _elo_function(self.player2[1][0]),
                    lambda: _elo_function(self.player2[1][1]),
                    integer,
                    "after",
                )[1],
                "PLAYER2_ELO": integer(_elo_function(self.player2[1][1])),
                "PLAYER1_MU_INCREASE": _change(
                    self.player1[1][0].mu,
                    self.player1[1][1].mu,
                    short_decimal,
                    "before",
                )[0],
                "PLAYER1_MU_DECREASE": _change(
                    self.player1[1][0].mu,
                    self.player1[1][1].mu,
                    short_decimal,
                    "before",
                )[1],
                "PLAYER1_MU": short_decimal(self.player1[1][1].mu),
                "PLAYER2_MU_INCREASE": _change(
                    self.player2[1][0].mu,
                    self.player2[1][1].mu,
                    short_decimal,
                    "before",
                )[0],
                "PLAYER2_MU_DECREASE": _change(
                    self.player2[1][0].mu,
                    self.player2[1][1].mu,
                    short_decimal,
                    "before",
                )[1],
                "PLAYER2_MU": short_decimal(self.player2[1][1].mu),
                "PLAYER1_SIGMA_INCREASE": _change(
                    self.player1[1][0].sigma,
                    self.player1[1][1].sigma,
                    short_decimal,
                    "after",
                )[0],
                "PLAYER1_SIGMA_DECREASE": _change(
                    self.player1[1][0].sigma,
                    self.player1[1][1].sigma,
                    short_decimal,
                    "after",
                )[1],
                "PLAYER1_SIGMA": short_decimal(self.player1[1][1].sigma),
                "PLAYER2_SIGMA_INCREASE": _change(
                    self.player2[1][0].sigma,
                    self.player2[1][1].sigma,
                    short_decimal,
                    "after",
                )[0],
                "PLAYER2_SIGMA_DECREASE": _change(
                    self.player2[1][0].sigma,
                    self.player2[1][1].sigma,
                    short_decimal,
                    "after",
                )[1],
                "PLAYER2_SIGMA": short_decimal(self.player2[1][1].sigma),
                "MATCH_DATE": datetime.now(_UTC).strftime("%A %d %B %Y %H:%M %Z"),
                "PLAYER1_WINNER": "winner" if self.winner == "player1" else "",
                "PLAYER2_WINNER": "winner" if self.winner == "player2" else "",
                "MATCH_WATERMARK": self.watermark,
                "PLAYER1_SCORE_BAR_OFFSET": (
                    "1"
                    if self.winner == "player1"
                    else str(self.player1[2] / self.player2[2])
                ),
                "PLAYER2_SCORE_BAR_OFFSET": (
                    "1"
                    if self.winner == "player2"
                    else str(self.player2[2] / self.player1[2])
                ),
                "PLAYER1_SCORE_WINNER": (
                    long_integer(self.player1[2]) if self.winner == "player1" else ""
                ),
                "PLAYER2_SCORE_WINNER": (
                    long_integer(self.player2[2]) if self.winner == "player2" else ""
                ),
                "PLAYER1_SCORE_LOSER": (
                    long_integer(self.player1[2]) if self.winner == "player2" else ""
                ),
                "PLAYER2_SCORE_LOSER": (
                    long_integer(self.player2[2]) if self.winner == "player1" else ""
                ),
                "RATING_MODEL": self.model.model_type.value,
            },
            f"{GRAPHICS}/1v1-after.svg",
            BANNER_SIZE,
        )


class SmallProfileGraphic(Graphic):
    osu_user: User
    rating: PlackettLuceRating
    rank: int
    model: ratings.RatingModel

    def __init__(
        self,
        osu_user: User,
        rating: PlackettLuceRating,
        rank: int,
        model: ratings.RatingModel,
    ):
        self.osu_user = osu_user
        self.rating = rating
        self.rank = rank
        self.model = model

    def render(self) -> tuple[dict[str, str], str, _Rectangle]:
        return (
            {
                "PLAYER_ELO_RANK": str(self.rank),
                "PLAYER_COVER_URL": self.osu_user.cover_url,
                "PLAYER_AVATAR_URL": self.osu_user.avatar_url,
                "PLAYER_NAME": (
                    self.osu_user.username[: min(9, len(self.osu_user.username))]
                    + ("…" if len(self.osu_user.username) > 9 else "")
                ),
                "PLAYER_RANK": long_integer(
                    unwrap(unwrap(self.osu_user.statistics).global_rank)
                ),
                "PLAYER_PP": integer(unwrap(unwrap(self.osu_user.statistics).pp)),
                "PLAYER_COUNTRY_CODE": self.osu_user.country_code,
                "PLAYER_COUNTRY": (
                    unwrap(self.osu_user.country).name[
                        : min(10, len(unwrap(self.osu_user.country).name))
                    ]
                    + ("…" if len(unwrap(self.osu_user.country).name) > 10 else "")
                ),
                "PLAYER_ELO": integer(_elo_function(self.rating)),
                "PLAYER_MU": short_decimal(self.rating.mu),
                "PLAYER_SIGMA": short_decimal(self.rating.sigma),
                "RATING_MODEL": self.model.model_type.value,
            },
            f"{GRAPHICS}/profile-small.svg",
            SMALL_PROFILE_SIZE,
        )


def render(graphic: Graphic) -> bytes:
    variable_mappings, filename, size = graphic.render()
    svg: str = ""
    with open(filename, "r", encoding="utf-8") as f:
        svg = f.read()
    for string in variable_mappings:
        svg = svg.replace(string, variable_mappings[string])

    result = subprocess.run(
        [
            INKSCAPE,
            "--export-type=png",
            "--export-filename=-",
            f"--export-width={size.width}",
            f"--export-height={size.height}",
            "--pipe",
        ],
        input=svg.encode(),
        capture_output=True,
        check=True,
    )
    return result.stdout
