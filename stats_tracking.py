from enum import Enum
from typing import Generic, TypeVar

from osu import Mod, Mods

from . import database

T = TypeVar("T")


class MatchType(Enum):
    one_v_one = 1


class MatchStatistic(Generic[T]):
    statistic: dict[MatchType, T]
    overall: T

    def __init__(self, statistic: dict[MatchType, T], overall: T) -> None:
        self.statistic = statistic
        self.overall = overall

    def __getitem__(self, match_type: MatchType) -> T:
        return self.statistic[match_type]


class CountedMatchStatistic(MatchStatistic):
    statistic: dict[MatchType, int]

    @property
    def overall(self) -> int:
        return sum(self.statistic.values())

    def __init__(self, statistic: dict[MatchType, int]):
        self.statistic = statistic


class MatchResult(Enum):
    win = 1
    loss = -1
    draw = 0


class ResultStatistics:
    statistics: dict[MatchResult, CountedMatchStatistic]

    def __init__(self, statistics: dict[MatchResult, CountedMatchStatistic]):
        self.statistics = statistics

    @property
    def matches_played(self) -> CountedMatchStatistic:
        return CountedMatchStatistic(
            {
                match_type: sum(
                    [statistic[match_type] for statistic in self.statistics.values()]
                )
                for match_type in MatchType
            }
        )

    @property
    def win_percentage(self) -> MatchStatistic[float]:
        return MatchStatistic(
            {
                match_type: (
                    self.statistics[MatchResult.win][match_type]
                    / self.matches_played[match_type]
                    if self.matches_played[match_type] > 0
                    else 0
                )
                for match_type in MatchType
            },
            (
                self.matches_played.overall / self.matches_played.overall * 100
                if self.matches_played.overall > 0
                else 0
            ),
        )


class PlayerStatistics:
    match_results: ResultStatistics

    mods_used: dict[Mod, CountedMatchStatistic]
    mod_combos_used: dict[Mods, CountedMatchStatistic]


class PlayerGlobalStatistics:
    model_statistics: dict[str, PlayerStatistics]

    @property
    def match_results(self) -> ResultStatistics:
        return ResultStatistics(
            {
                result: CountedMatchStatistic(
                    {
                        match_type: sum(
                            model_statistics.match_results.statistics[result][
                                match_type
                            ]
                            for model_statistics in self.model_statistics.values()
                        )
                        for match_type in MatchType
                    }
                )
                for result in MatchResult
            }
        )

    @property
    def mods_used(self) -> dict[Mod, CountedMatchStatistic]:
        return {
            mod: CountedMatchStatistic(
                {
                    match_type: sum(
                        model_statistics.mods_used[mod][match_type]
                        for model_statistics in self.model_statistics.values()
                    )
                    for match_type in MatchType
                }
            )
            for mod in Mod
        }

    @property
    def mod_combos_used(self) -> dict[Mods, CountedMatchStatistic]:
        return {
            combo: CountedMatchStatistic(
                {
                    match_type: sum(
                        model_statistics.mod_combos_used[combo][match_type]
                        for model_statistics in self.model_statistics.values()
                    )
                    for match_type in MatchType
                }
            )
            for combo in Mods
        }


class GlobalStatistics(dict[int, PlayerGlobalStatistics]):
    def __init__(self):
        super().__init__()


global_stats: GlobalStatistics = GlobalStatistics()
