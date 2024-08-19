import sqlite3
from typing import Never, override

import discord
import osu
from openskill.models.weng_lin.plackett_luce import PlackettLuceRating

from .misc.constants import (
    DiscordUserId,
    IdType,
    OsuUserId,
    RatingDataType,
    RatingModelType,
)

DATABASE: str = "./osuvs.db"

DISCORD_OSU_TABLE: str = "discord_osu"
OSU_RATINGS_TABLE: str = "osu_ratings"

DISCORD_ID_COLUMN: str = "discord_id"
OSU_ID_COLUMN: str = "osu_id"

MU_COLUMN: str = "mu"
SIGMA_COLUMN: str = "sigma"


con = sqlite3.connect(DATABASE)
cur = con.cursor()


class DiscordLinksDatabase:
    table: str
    columns: dict[IdType, str]

    def __init__(self, table: str, columns: dict[IdType, str]) -> None:
        super().__init__()
        self.table = table
        self.columns = columns

    def __getitem__(
        self, discord_user: discord.Member | discord.User | DiscordUserId
    ) -> OsuUserId:
        cur.execute(
            f"""SELECT {self.columns[IdType.OSU_ID]}
                FROM {self.table}
                WHERE {self.columns[IdType.DISCORD_ID]} = ?""",
            (
                (
                    discord_user.id
                    if isinstance(discord_user, discord.Member | discord.User)
                    else discord_user
                ),
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise KeyError(f"No osu user linked to Discord user {discord_user}")
        return result[0]

    def __setitem__(
        self,
        discord_user: discord.Member | discord.User | DiscordUserId,
        osu_user: osu.User | OsuUserId,
    ) -> None:
        data: dict[str, int] = {
            "discord_id": (
                discord_user.id
                if isinstance(discord_user, discord.Member | discord.User)
                else discord_user
            ),
            "osu_id": osu_user.id if isinstance(osu_user, osu.User) else osu_user,
        }
        cur.execute(
            f"""INSERT OR REPLACE INTO {self.table}
                (`{self.columns[IdType.DISCORD_ID]}`, `{self.columns[IdType.OSU_ID]}`)
                VALUES (:discord_id, :osu_id)""",
            data,
        )
        con.commit()

    def __delitem__(
        self, discord_user: discord.Member | discord.User | DiscordUserId
    ) -> None:
        cur.execute(
            f"""DELETE FROM {self.table}
                WHERE {self.columns[IdType.DISCORD_ID]} =?""",
            (
                (
                    discord_user.id
                    if isinstance(discord_user, discord.Member | discord.User)
                    else discord_user
                ),
            ),
        )
        con.commit()

    def __contains__(
        self, discord_user: discord.Member | discord.User | DiscordUserId
    ) -> bool:
        cur.execute(
            f"""SELECT 1
                FROM {self.table}
                WHERE {self.columns[IdType.DISCORD_ID]} =?""",
            (
                (
                    discord_user.id
                    if isinstance(discord_user, discord.Member | discord.User)
                    else discord_user
                ),
            ),
        )
        return cur.fetchone() is not None


class AbstractOsuRatingsDatabase:
    table: str
    columns: dict[IdType | RatingDataType, str]

    def __init__(self, table: str, columns: dict[IdType | RatingDataType, str]) -> None:
        self.table = table
        self.columns = columns

    def __getitem__(self, key) -> Never:
        raise NotImplementedError("Subclass must implement __getitem__ method")

    def __setitem__(self, key, value) -> Never:
        raise NotImplementedError("Subclass must implement __setitem__ method")

    def __delitem__(self, osu_user: osu.User | OsuUserId) -> None:
        cur.execute(
            f"""DELETE FROM {self.table}
                WHERE {self.columns[IdType.OSU_ID]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )
        con.commit()

    def __contains__(self, osu_user: osu.User | OsuUserId) -> bool:
        cur.execute(
            f"""SELECT 1
                FROM {self.table}
                WHERE {self.columns[IdType.OSU_ID]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )
        return cur.fetchone() is not None

    def init_blank_ratings(self, osu_user: osu.User | OsuUserId) -> None:
        cur.execute(
            f"""INSERT INTO {self.table}
                ({self.columns[IdType.OSU_ID]})
                VALUES (?)""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )
        con.commit()


class OsuRatingsDatabase(AbstractOsuRatingsDatabase):
    @override
    def __init__(
        self, table: str, columns: dict[IdType | RatingDataType, str], model: str
    ) -> None:
        super().__init__(
            table,
            {
                IdType.OSU_ID: columns[IdType.OSU_ID],
                RatingDataType.MU: f"{model}_{columns[RatingDataType.MU]}",
                RatingDataType.SIGMA: f"{model}_{columns[RatingDataType.SIGMA]}",
            },
        )

    @override
    def __getitem__(
        self, osu_user: osu.User | OsuUserId
    ) -> dict[RatingDataType, float] | PlackettLuceRating:
        cur.execute(
            f"""SELECT {self.columns[RatingDataType.MU]}, {self.columns[RatingDataType.SIGMA]}
                FROM {self.table}
                WHERE {self.columns[IdType.OSU_ID]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )
        result = cur.fetchone()
        if result is None:
            raise KeyError(f"No ratings found for osu user {osu_user}")
        return {
            RatingDataType.MU: result[0],
            RatingDataType.SIGMA: result[1],
        }

    @override
    def __setitem__(
        self,
        osu_user: osu.User | OsuUserId,
        value: PlackettLuceRating | dict[RatingDataType, float],
    ) -> None:
        data: dict[str, float | int | OsuUserId] = {
            self.columns[IdType.OSU_ID]: (
                osu_user.id if isinstance(osu_user, osu.User) else osu_user
            ),
            self.columns[RatingDataType.MU]: (
                value.mu
                if isinstance(value, PlackettLuceRating)
                else value[RatingDataType.MU]
            ),
            self.columns[RatingDataType.SIGMA]: (
                value.sigma
                if isinstance(value, PlackettLuceRating)
                else value[RatingDataType.SIGMA]
            ),
        }
        if osu_user in self:
            cur.execute(
                f"""UPDATE {self.table}
                    SET
                        {self.columns[RatingDataType.MU]} = :{self.columns[RatingDataType.MU]},
                        {self.columns[RatingDataType.SIGMA]} = :{self.columns[RatingDataType.SIGMA]}
                    WHERE {self.columns[IdType.OSU_ID]} = :{self.columns[IdType.OSU_ID]}""",
                data,
            )
        else:
            cur.execute(
                f"""INSERT INTO {self.table}
                    ({self.columns[IdType.OSU_ID]},
                     {self.columns[RatingDataType.MU]},
                     {self.columns[RatingDataType.SIGMA]})
                    VALUES (:{self.columns[IdType.OSU_ID]},
                            :{self.columns[RatingDataType.MU]},
                            :{self.columns[RatingDataType.SIGMA]})""",
                data,
            )
        con.commit()

    @override
    def __delitem__(self, osu_user: osu.User | OsuUserId) -> None:
        cur.execute(
            f"""UPDATE {self.table}
                SET
                    {self.columns[RatingDataType.MU]} = NULL,
                    {self.columns[RatingDataType.SIGMA]} = NULL
                WHERE {self.columns[IdType.OSU_ID]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )

    def update(
        self,
        values: (
            dict[osu.User, PlackettLuceRating] | dict[OsuUserId, PlackettLuceRating]
        ),
    ) -> None:
        cur.executemany(
            f"""UPDATE {self.table}
                SET
                    {self.columns[RatingDataType.MU]} = :{self.columns[RatingDataType.MU]},
                    {self.columns[RatingDataType.SIGMA]} = :{self.columns[RatingDataType.SIGMA]}
                WHERE {self.columns[IdType.OSU_ID]} = :{self.columns[IdType.OSU_ID]}""",
            [
                (
                    osu_user.id if isinstance(osu_user, osu.User) else osu_user,
                    (
                        value.mu
                        if isinstance(value, PlackettLuceRating)
                        else value[RatingDataType.MU]
                    ),
                    (
                        value.sigma
                        if isinstance(value, PlackettLuceRating)
                        else value[RatingDataType.SIGMA]
                    ),
                )
                for osu_user, value in values.items()
            ],
        )
        con.commit()

    def dict(self) -> dict[OsuUserId, dict[RatingDataType, float]]:
        cur.execute(
            f"""SELECT
                    {self.columns[IdType.OSU_ID]},
                    {self.columns[RatingDataType.MU]},
                    {self.columns[RatingDataType.SIGMA]}
                FROM {self.table}"""
        )
        return {
            osu_id: {
                RatingDataType.MU: mu,
                RatingDataType.SIGMA: sigma,
            }
            for osu_id, mu, sigma in cur.fetchall()
            if mu is not None and sigma is not None
        }


discord_links = DiscordLinksDatabase(
    DISCORD_OSU_TABLE,
    {IdType.DISCORD_ID: DISCORD_ID_COLUMN, IdType.OSU_ID: OSU_ID_COLUMN},
)

ratings = AbstractOsuRatingsDatabase(OSU_RATINGS_TABLE, {IdType.OSU_ID: OSU_ID_COLUMN})
models = {
    model: OsuRatingsDatabase(
        OSU_RATINGS_TABLE,
        {
            IdType.OSU_ID: OSU_ID_COLUMN,
            RatingDataType.MU: MU_COLUMN,
            RatingDataType.SIGMA: SIGMA_COLUMN,
        },
        model.value,
    )
    for model in RatingModelType
}
