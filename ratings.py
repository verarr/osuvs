from copy import deepcopy
from functools import reduce
from operator import iconcat

import osu
from openskill.models import PlackettLuce, PlackettLuceRating
from sortedcollections import ValueSortedDict
from unopt import unwrap

import database
from misc.constants import OsuUserId, RatingDataType, RatingModelType


def _ranking_key(rating: PlackettLuceRating) -> float:
    return rating.ordinal(alpha=-1)


DefaultModelType = PlackettLuce


class RatingModel:
    model: PlackettLuce
    osu_ratings_links: ValueSortedDict
    model_type: RatingModelType
    db: database.OsuRatingsDatabase

    def __init__(self, model: PlackettLuce, model_type: RatingModelType):
        self.model = model
        self.osu_ratings_links = ValueSortedDict(_ranking_key)
        self.model_type = model_type
        self.db = database.models[model_type]
        self._load_ratings()

    def _load_ratings(self):
        ratings = self.db.dict() or {}
        buffer: dict[int, PlackettLuceRating] = {}
        for osu_id, rating in ratings.items():
            assert not isinstance(osu_id, osu.User)
            assert not isinstance(rating, PlackettLuceRating)
            if (
                rating[RatingDataType.MU] is not None
                and rating[RatingDataType.SIGMA] is not None
            ):
                buffer[osu_id] = self.model.create_rating(
                    [
                        rating[RatingDataType.MU],
                        rating[RatingDataType.SIGMA],
                    ],
                    name=str(osu_id),
                )
        self._update(list(buffer.values()))

    def _update(
        self, ratings: list[PlackettLuceRating] | dict[osu.User, PlackettLuceRating]
    ):
        self.osu_ratings_links.update(
            {int(unwrap(rating.name)): rating for rating in ratings}
            if isinstance(ratings, list)
            else ratings
        )

    def update(
        self, ratings: list[PlackettLuceRating] | dict[osu.User, PlackettLuceRating]
    ):
        if len(ratings) == 0:
            return
        self._update(ratings)
        if isinstance(ratings, list):
            self.db.update(
                {OsuUserId(unwrap(rating.name)): rating for rating in ratings}
            )
        else:
            self.db.update(ratings)

    def __getitem__(self, user: osu.User) -> PlackettLuceRating:
        if user not in self:
            self.init_rating(user)
        return self.osu_ratings_links[user.id]

    def __contains__(self, user: osu.User) -> bool:
        return user.id in self.osu_ratings_links

    def __setitem__(self, user: osu.User, value: PlackettLuceRating) -> None:
        self.update({user: value})

    def init_rating(self, user: osu.User) -> None:
        rating = self.model.rating(name=str(user.id))
        self.update([rating])

    def rate_match(
        self,
        teams: list[list[osu.User]],
        scores: list[list[int | float]] | None = None,
        dry_run: bool = False,
    ) -> list[list[PlackettLuceRating]]:
        teams_ratings: list[list[PlackettLuceRating]] = [
            [self[user] for user in team] for team in teams
        ]
        if dry_run:
            teams_ratings = deepcopy(teams_ratings)

        teams_ratings = self.model.rate(
            teams_ratings,
            scores=[sum(team_scores) for team_scores in scores] if scores else None,
            weights=scores,
        )
        players: list[PlackettLuceRating] = reduce(iconcat, teams_ratings, [])
        if not dry_run:
            self.update(players)
        return teams_ratings


rating_models: dict[RatingModelType, RatingModel] = {
    rating_model: RatingModel(DefaultModelType(), rating_model)
    for rating_model in RatingModelType
}


def rating_exists(user: osu.User) -> bool:
    return any(user in rating_model for rating_model in rating_models.values())
