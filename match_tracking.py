from asyncio import InvalidStateError, create_task, sleep

from osu import Beatmap, SoloScore, User, UserScoreType
from unopt import unwrap

from . import osu_api as osu_api


class MatchVoidException(Exception):
    """Exception to indicate that a match cannot be completed due to lack of scores."""


async def _check_scores(teams: list[list[User]], beatmap: Beatmap):
    player_scores: list[list[int]] = []
    total_score = 0
    everyone_finished = True
    for team in teams:
        team_scores: list[int] = []
        team_score = 0
        for player in team:
            try:
                scores = osu_api.client._client.get_user_scores(
                    player.id, UserScoreType.RECENT, mode=beatmap.mode
                )
                valid_scores = [
                    (score.total_score if isinstance(score, SoloScore) else score.score)
                    for score in scores
                    if (
                        (score.beatmap_id == beatmap.id)
                        if isinstance(score, SoloScore)
                        else (unwrap(score.beatmap).id == beatmap.id)
                    )
                ]
                score = valid_scores[0]
            except IndexError:
                score = 0
                everyone_finished = False
            team_scores.append(score)
            team_score += score
        player_scores.append(team_scores)
        total_score += team_score
    return player_scores, total_score, everyone_finished


async def do_match(teams: list[list[User]], beatmap: Beatmap) -> list[list[int]]:
    max_time = max(beatmap.total_length * 1.5, 60)
    await sleep(beatmap.total_length)
    player_scores: list[list[int]]
    for _ in range(int((max_time - beatmap.total_length) // 10)):
        task = create_task(_check_scores(teams, beatmap))
        await sleep(10)
        try:
            player_scores, _, everyone_finished = task.result()
        except InvalidStateError:
            task.cancel()
            continue
        if everyone_finished:
            return player_scores
    await sleep((max_time - beatmap.total_length) % 10)
    player_scores, total_score, _ = await _check_scores(teams, beatmap)
    if total_score == 0:
        raise MatchVoidException("No scores found for the given beatmap.")
    return player_scores
