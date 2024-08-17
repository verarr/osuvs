import sqlite3

DATABASE: str = "./osuvs.db"

DISCORD_OSU_TABLE: str = "discord_osu"
OSU_RATINGS_TABLE: str = "osu_ratings"

models: list[str] = input(
    "Enter the names of the rating models (separated by spaces): "
).split()
if models == []:
    models = ["osu", "taiko", "fruits", "mania"]

DISCORD_OSU_SPEC: str = """
    discord_id UNSIGNED BIGINT PRIMARY KEY,
    osu_id UNSIGNED INT
"""
OSU_RATINGS_SPEC = """
    osu_id UNSIGNED INT PRIMARY KEY,
""" + ",\n".join(
    f"{model}_mu REAL, {model}_sigma REAL" for model in models
)


con = sqlite3.connect(DATABASE)
cur = con.cursor()

cur.execute(f"CREATE TABLE {DISCORD_OSU_TABLE}({DISCORD_OSU_SPEC})")
cur.execute(f"CREATE TABLE {OSU_RATINGS_TABLE}({OSU_RATINGS_SPEC})")

con.commit()
con.close()
