import sqlite3
from typing import Never, override

import discord
import osu
from openskill.models.weng_lin.plackett_luce import PlackettLuceRating

from misc.osuvs_constants import *

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
            f"""SELECT {self.columns[IdType.osu_id]}
                FROM {self.table}
                WHERE {self.columns[IdType.discord_id]} = ?""",
            (
                (
                    discord_user.id
                    if isinstance(discord_user, discord.Member | discord.User)
                    else discord_user
                ),
            ),
        )
        result = cur.fetchone()
        if result is not None:
            return result[0]
        else:
            raise KeyError(f"No osu user linked to Discord user {discord_user}")

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
                (`{self.columns[IdType.discord_id]}`, `{self.columns[IdType.osu_id]}`)
                VALUES (:discord_id, :osu_id)""",
            data,
        )
        con.commit()

    def __delitem__(
        self, discord_user: discord.Member | discord.User | DiscordUserId
    ) -> None:
        cur.execute(
            f"""DELETE FROM {self.table}
                WHERE {self.columns[IdType.discord_id]} =?""",
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
                WHERE {self.columns[IdType.discord_id]} =?""",
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

    def __getitem__(self) -> Never:
        raise NotImplementedError("Subclass must implement __getitem__ method")

    def __setitem__(self) -> Never:
        raise NotImplementedError("Subclass must implement __setitem__ method")

    def __delitem__(self, osu_user: osu.User | OsuUserId) -> None:
        cur.execute(
            f"""DELETE FROM {self.table}
                WHERE {self.columns[IdType.osu_id]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )
        con.commit()

    def __contains__(self, osu_user: osu.User | OsuUserId) -> bool:
        cur.execute(
            f"""SELECT 1
                FROM {self.table}
                WHERE {self.columns[IdType.osu_id]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )
        return cur.fetchone() is not None

    def init_blank_ratings(self, osu_user: osu.User | OsuUserId) -> None:
        cur.execute(
            f"""INSERT INTO {self.table}
                ({self.columns[IdType.osu_id]})
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
                IdType.osu_id: columns[IdType.osu_id],
                RatingDataType.mu: f"{model}_{columns[RatingDataType.mu]}",
                RatingDataType.sigma: f"{model}_{columns[RatingDataType.sigma]}",
            },
        )

    @override
    def __getitem__(
        self, osu_user: osu.User | OsuUserId
    ) -> dict[RatingDataType, float] | PlackettLuceRating:
        cur.execute(
            f"""SELECT {self.columns[RatingDataType.mu]}, {self.columns[RatingDataType.sigma]}
                FROM {self.table}
                WHERE {self.columns[IdType.osu_id]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )
        result = cur.fetchone()
        if result is not None:
            return {
                RatingDataType.mu: result[0],
                RatingDataType.sigma: result[1],
            }
        else:
            raise KeyError(f"No ratings found for osu user {osu_user}")

    @override
    def __setitem__(
        self,
        osu_user: osu.User | OsuUserId,
        value: PlackettLuceRating | dict[RatingDataType, float],
    ) -> None:
        data: dict[str, float | int | OsuUserId] = {
            self.columns[IdType.osu_id]: (
                osu_user.id if isinstance(osu_user, osu.User) else osu_user
            ),
            self.columns[RatingDataType.mu]: (
                value.mu
                if isinstance(value, PlackettLuceRating)
                else value[RatingDataType.mu]
            ),
            self.columns[RatingDataType.sigma]: (
                value.sigma
                if isinstance(value, PlackettLuceRating)
                else value[RatingDataType.sigma]
            ),
        }
        if osu_user in self:
            cur.execute(
                f"""UPDATE {self.table}
                    SET
                        {self.columns[RatingDataType.mu]} = :{self.columns[RatingDataType.mu]},
                        {self.columns[RatingDataType.sigma]} = :{self.columns[RatingDataType.sigma]}
                    WHERE {self.columns[IdType.osu_id]} = :{self.columns[IdType.osu_id]}""",
                data,
            )
        else:
            cur.execute(
                f"""INSERT INTO {self.table}
                    ({self.columns[IdType.osu_id]},
                     {self.columns[RatingDataType.mu]},
                     {self.columns[RatingDataType.sigma]})
                    VALUES (:{self.columns[IdType.osu_id]},
                            :{self.columns[RatingDataType.mu]},
                            :{self.columns[RatingDataType.sigma]})""",
                data,
            )
        con.commit()

    @override
    def __delitem__(self, osu_user: osu.User | OsuUserId) -> None:
        cur.execute(
            f"""UPDATE {self.table}
                SET
                    {self.columns[RatingDataType.mu]} = NULL,
                    {self.columns[RatingDataType.sigma]} = NULL
                WHERE {self.columns[IdType.osu_id]} =?""",
            (osu_user.id if isinstance(osu_user, osu.User) else osu_user,),
        )

    def dict(self) -> dict[OsuUserId, dict[RatingDataType, float]]:
        cur.execute(
            f"""SELECT
                    {self.columns[IdType.osu_id]},
                    {self.columns[RatingDataType.mu]},
                    {self.columns[RatingDataType.sigma]}
                FROM {self.table}"""
        )
        return {
            osu_id: {
                RatingDataType.mu: mu,
                RatingDataType.sigma: sigma,
            }
            for osu_id, mu, sigma in cur.fetchall()
            if mu is not None and sigma is not None
        }


discord_links = DiscordLinksDatabase(
    DISCORD_OSU_TABLE,
    {IdType.discord_id: DISCORD_ID_COLUMN, IdType.osu_id: OSU_ID_COLUMN},
)

ratings = AbstractOsuRatingsDatabase(OSU_RATINGS_TABLE, {IdType.osu_id: OSU_ID_COLUMN})
models = {
    model: OsuRatingsDatabase(
        OSU_RATINGS_TABLE,
        {
            IdType.osu_id: OSU_ID_COLUMN,
            RatingDataType.mu: MU_COLUMN,
            RatingDataType.sigma: SIGMA_COLUMN,
        },
        model.value,
    )
    for model in RatingModelType
}
