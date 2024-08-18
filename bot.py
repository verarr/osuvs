import pickle
import sys
from copy import deepcopy
from io import BytesIO
from time import gmtime, strftime, time
from typing import Literal

import discord
from discord import app_commands
from osu import Beatmap, GameModeStr
from requests import HTTPError
from unopt import unwrap

import osuvs_db as database
import osuvs_graphics as graphics
import osuvs_matches as matches
import osuvs_osu_api as osu_api
import osuvs_ratings as ratings
from misc.osuvs_constants import OsuBeatmapId, RatingModelType
from misc.osuvs_utils import parse_beatmap_url

SECRETS_DIR: str = "./secrets"

# Discord API setup
try:
    with open(f"{SECRETS_DIR}/token.pickle", "rb") as f:
        TOKEN = pickle.load(f)
except FileNotFoundError:
    print("Token file not found.")
    sys.exit(1)

GUILD = discord.Object(id=1271199252667830363)  # my server shshshshshshshshsh
OWO_BOT_ID: int = 289066747443675143


class MyClient(discord.Client):
    """Customized Discord client"""

    guild: discord.Guild
    owo_bot: discord.Member | None

    def __init__(self, *, intents: discord.Intents) -> None:
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)


client_intents = discord.Intents.default()
client_intents.members = True
# intents.message_content = True

client = MyClient(intents=client_intents)


# bot functionality

MODESTR = Literal["osu", "taiko", "fruits", "mania"]


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {unwrap(client.user).id})")
    print("------")

    client.guild = unwrap(client.get_guild(GUILD.id))
    print(f"Got guild: {client.guild.name}")
    client.owo_bot = client.guild.get_member(OWO_BOT_ID)
    print(f"owo bot is here: {unwrap(client.owo_bot).id}")

    print("------")
    print("Ready!")


class Accept(discord.ui.View):
    def __init__(self, allowed_users: list[discord.User | discord.Member]):
        super().__init__()
        self.value = None
        self.allowed_users = allowed_users

    @discord.ui.button(label="Accept", emoji="🤝", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user in self.allowed_users:
            self.value = True
            await interaction.response.defer()
            self.stop()
        else:
            await interaction.response.send_message(
                "You are not allowed to perform this action right now.", ephemeral=True
            )

    @discord.ui.button(label="Decline", emoji="✋", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user in self.allowed_users:
            self.value = False
            await interaction.response.defer()
            self.stop()
        else:
            await interaction.response.send_message(
                "You are not allowed to perform this action right now.", ephemeral=True
            )


class OsuBeatmapDownloads(discord.ui.View):
    def __init__(self, beatmap: Beatmap):
        super().__init__(timeout=None)
        self.beatmap = beatmap
        self.add_item(
            discord.ui.Button(
                label="Download from ppy.sh",
                emoji="⚪",
                url="https://osu.ppy.sh/beatmapsets/"
                + str(beatmap.beatmapset_id)
                + "#"
                + beatmap.mode.name.lower()
                + "/"
                + str(beatmap.id),
            )
        )
        # uncomment when discord adds support for other url schemes
        #
        # self.add_item(
        #     discord.ui.Button(
        #         label="osu!direct",
        #         emoji="🔗",
        #         url="osu://b/" + str(beatmap.id),
        #     )
        # )
        
        self.add_item(
            discord.ui.Button(
                label="catboy.best",
                emoji="🥺",
                url="https://catboy.best/d/" + str(beatmap.beatmapset_id),
            )
        )


@app_commands.default_permissions(manage_guild=True)
class AdminCommands(app_commands.Group):
    pass


admin_group = AdminCommands(
    name="admin",
    description="Commands related to managing this bot on a server.",
)
simulate_group = app_commands.Group(name="simulate", description="Simulate matches.")
link_admin_group = app_commands.Group(
    name="osu",
    description="Commands related to managing links between osu! usernames and Discord accounts.",
)

link_group = app_commands.Group(
    name="osu",
    description="Commands related to linking your osu! username to your Discord account.",
)


@client.tree.command()
@app_commands.describe(
    opponent="The person you want to challenge", beatmap="The beatmap you want to play"
)
async def challenge(
    interaction: discord.Interaction, opponent: discord.Member, beatmap: str
) -> None:
    """Challenge someone to a game on one beatmap"""

    channel = unwrap(interaction.channel)
    assert isinstance(channel, discord.TextChannel)

    await interaction.response.defer(ephemeral=True, thinking=True)

    # check beatmap
    try:
        _, mode, diff_id = parse_beatmap_url(beatmap)
    except ValueError:
        return await interaction.followup.send(
            "Invalid beatmap URL. Please provide a valid beatmap URL.",
            ephemeral=True,
        )
    try:
        beatmap_info = osu_api.client.beatmaps[OsuBeatmapId(diff_id)]
    except HTTPError:
        return await interaction.followup.send(
            "Beatmap not found. Please provide a valid beatmap URL.",
            ephemeral=True,
        )

    # check players
    try:
        challenger_osu = osu_api.client.users[
            (database.discord_links[interaction.user], mode)
        ]
    except KeyError:
        return await interaction.followup.send(
            "You haven't linked your profile yet. "
            + "This unfortunately means you can't challenge someone."
            + "\n"
            + "Use `/link` to link your profile.",
            ephemeral=True,
        )
    try:
        opponent_osu = osu_api.client.users[(database.discord_links[opponent], mode)]
    except KeyError:
        return await interaction.followup.send(
            "Your opponent hasn't linked their profile yet. "
            + "This unfortunately means you can not challenge them.",
            ephemeral=True,
        )

    rating_model = ratings.rating_models[RatingModelType.from_gamemodestr(mode)]

    challenger_rating = rating_model[challenger_osu]
    opponent_rating = rating_model[opponent_osu]

    graphic = discord.File(
        BytesIO(
            graphics.render(
                graphics.OneVOneBeforeGraphic(
                    (opponent_osu, opponent_rating),
                    (challenger_osu, challenger_rating),
                    rating_model,
                )
            )
        ),
        filename="match-banner.png",
    )
    accept_view = Accept([opponent])
    downloads_view = OsuBeatmapDownloads(beatmap_info)

    thread = await channel.create_thread(
        name=f"{interaction.user.display_name} vs {opponent.display_name}"
        + " "
        + f"({strftime('%A %B %d', gmtime())})",
        type=discord.ChannelType.private_thread,
    )
    await thread.add_user(unwrap(client.owo_bot))
    await thread.send(
        f"Watch out {opponent.mention}, "
        + f"{interaction.user.mention} wants to challenge you!",
        file=graphic,
        view=accept_view,
    )
    del graphic
    await thread.send(
        "Beatmap to play: ["
        + f"**{unwrap(beatmap_info.beatmapset).title}** - {unwrap(beatmap_info.beatmapset).artist} "
        + f"**[{beatmap_info.version}]**"
        + f" by {unwrap(beatmap_info.beatmapset).creator}"
        + "]("
        + beatmap_info.url
        + ")",
        view=downloads_view,
    )

    await interaction.followup.send(
        f"Challenge sent! Look in {thread.jump_url}.", ephemeral=True
    )

    await accept_view.wait()
    accept_view.clear_items()
    match accept_view.value:
        case False | None:
            await thread.send(
                f"Sorry {interaction.user.mention}, your opponent has declined your challenge."
            )
            await thread.edit(locked=True)
            return
        case True:
            await thread.send(
                "Alright, bring it on! Match will end "
                + f"<t:{int(time() + max(beatmap_info.total_length * 1.5, 60))}:R>"
                + "."
            )

    try:
        scores: list[list[int | float]] = [
            list(team_scores)
            for team_scores in await matches.do_match(
                [[challenger_osu], [opponent_osu]], beatmap_info
            )
        ]
    except matches.MatchVoidException:
        await thread.send("No player set any valid scores.")
        return
    teams = [[challenger_osu], [opponent_osu]]

    challenger_rating = deepcopy(challenger_rating)
    opponent_rating = deepcopy(opponent_rating)

    rating_model.rate_match(teams, scores=scores)

    challenger_rating_after = rating_model[challenger_osu]
    opponent_rating_after = rating_model[opponent_osu]
    winner: Literal["challenger", "opponent"]
    if scores[0][0] - scores[1][0] > 0:
        winner = "challenger"
    elif scores[0][0] - scores[1][0] < 0:
        winner = "opponent"
    else:
        await thread.send("It's a draw. (how???)")
        return

    winner_b: Literal["player1", "player2"]
    match winner:
        case "opponent":
            winner_b = "player1"
        case "challenger":
            winner_b = "player2"
    graphic = discord.File(
        BytesIO(
            graphics.render(
                graphics.OneVOneAfterGraphic(
                    (
                        opponent_osu,
                        (opponent_rating, opponent_rating_after),
                        int(scores[1][0]),
                    ),
                    (
                        challenger_osu,
                        (challenger_rating, challenger_rating_after),
                        int(scores[0][0]),
                    ),
                    rating_model,
                    winner=winner_b,
                )
            )
        ),
        filename="match-banner.png",
    )

    await thread.send("Match over! Here are the results:", file=graphic)


@client.tree.command()
@app_commands.rename(model="mode")
@app_commands.describe(
    model="Gamemode / Ruleset", player="Player whose profile to check"
)
async def profile(
    interaction: discord.Interaction,
    model: MODESTR = "osu",
    player: discord.Member | None = None,
):
    """Check a player's profile."""
    try:
        osu_id = database.discord_links[player or interaction.user]
    except KeyError:
        return await interaction.response.send_message(
            "You have not linked your profile yet. Use `/link` to do so.",
            ephemeral=True,
        )
    mode = GameModeStr(model)
    osu_user = osu_api.client.users[(osu_id, mode)]

    await interaction.response.defer(thinking=True)

    rating_model = ratings.rating_models[RatingModelType(model)]

    rating = rating_model[osu_user]

    await interaction.followup.send(
        "",
        file=discord.File(
            BytesIO(
                graphics.render(
                    graphics.SmallProfileGraphic(
                        osu_user,
                        rating,
                        rating_model.osu_ratings_links.index(osu_user.id) + 1,
                        rating_model,
                    )
                )
            ),
            filename="profile-small.png",
        ),
    )


@link_group.command()
@app_commands.describe(username="Your username in osu!.")
async def link(interaction: discord.Interaction, username: str):
    """Link your osu! username to your Discord account."""
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        osu_user = osu_api.client.users[(username, None)]
    except HTTPError:
        return await interaction.followup.send("User not found.", ephemeral=True)

    database.discord_links[interaction.user] = osu_user
    if not ratings.rating_exists(osu_user):
        database.ratings.init_blank_ratings(osu_user)

    await interaction.followup.send(
        f"Linked **{username}** (id: `{osu_user.id}`) to your Discord account.",
        ephemeral=True,
    )


@link_group.command()
async def unlink(interaction: discord.Interaction):
    """Unlink your osu! username from your Discord account."""
    await interaction.response.defer(ephemeral=True, thinking=True)

    if interaction.user not in database.discord_links:
        return await interaction.followup.send(
            "You have not linked your profile yet. No action was performed.",
            ephemeral=True,
        )

    del database.discord_links[interaction.user]
    await interaction.followup.send(
        "Unlinked your Discord account from your osu! profile.", ephemeral=True
    )


@link_admin_group.command(name="link")
@app_commands.describe(
    username="osu! username to assign.", member="Member to assign username to."
)
async def admin_link(
    interaction: discord.Interaction, username: str, member: discord.Member
):
    """Link an osu! username to a Discord account."""
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        osu_user = osu_api.client.users[(username, None)]  # type: ignore
    except HTTPError:
        return await interaction.followup.send("User not found.", ephemeral=True)

    database.discord_links[member or interaction.user] = osu_user
    if not ratings.rating_exists(osu_user):
        database.ratings.init_blank_ratings(osu_user)

    await interaction.followup.send(
        f"Linked **{username}** (id: `{osu_user.id}`) to **{member.mention}**'s Discord account.",
        ephemeral=True,
    )


@link_admin_group.command(name="unlink")
async def admin_unlink(interaction: discord.Interaction, member: discord.Member):
    """Unlink the osu! username assigned to a Discord account."""
    await interaction.response.defer(ephemeral=True, thinking=True)

    if member in database.discord_links:
        return await interaction.followup.send(
            f"No profile linked to this {member.mention}. No action was performed.",
            ephemeral=True,
        )

    del database.discord_links[member]
    await interaction.followup.send(
        f"Unlinked **{member.mention}**'s Discord account from their osu! profile.",
        ephemeral=True,
    )


@simulate_group.command(name="1v1")
@app_commands.describe(player_1="Winning player.", player_2="Losing player.")
async def simulate_1v1(
    interaction: discord.Interaction,
    player_1: discord.Member,
    player_2: discord.Member,
    model: RatingModelType = RatingModelType.OSU,
    dry_run: bool = True,
):
    """Simulate a 1v1 match between two players."""

    try:
        player1_osu = osu_api.client.users[
            (database.discord_links[player_1], GameModeStr(model.value))
        ]
        player2_osu = osu_api.client.users[
            (database.discord_links[player_2], GameModeStr(model.value))
        ]
    except KeyError:
        return await interaction.response.send_message(
            "Both players must have linked their profiles.",
            ephemeral=True,
        )

    await interaction.response.defer(thinking=True)

    rating_model = ratings.rating_models[model]

    player1_rating = deepcopy(rating_model[player1_osu])
    player2_rating = deepcopy(rating_model[player2_osu])

    ratings_after = rating_model.rate_match(
        [[player1_osu], [player2_osu]], dry_run=dry_run
    )

    player1_rating_after = ratings_after[0][0]
    player2_rating_after = ratings_after[1][0]

    graphic = discord.File(
        BytesIO(
            graphics.render(
                graphics.OneVOneAfterGraphic(
                    (player1_osu, (player1_rating, player1_rating_after), 1_000_000),
                    (player2_osu, (player2_rating, player2_rating_after), 0),
                    rating_model,
                    winner="player1",
                    watermark="SIMULATION" if dry_run else "ARTIFICIAL RESULTS",
                )
            )
        ),
        filename="match-banner.png",
    )

    await interaction.followup.send(
        f"## Match results ({"not " if dry_run else ""}saved):"
        + "\n\nplayer 1 ({player_1.mention}):\n```"
        + str(player1_rating_after)
        + f"\n```\nplayer 2 ({player_2.mention}):\n```"
        + str(player2_rating_after)
        + "\n```",
        file=graphic,
        allowed_mentions=discord.AllowedMentions.none(),
    )


client.tree.add_command(link_group)

admin_group.add_command(link_admin_group)
admin_group.add_command(simulate_group)
client.tree.add_command(admin_group)


# start bot
client.run(TOKEN)
