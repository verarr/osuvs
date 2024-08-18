# osuvs

A WIP alternative ranking system for osu! (and self-proclaimed successor of
o!rl)

> [!IMPORTANT]
>
> This project is unfinished, heavily Work-In-Progress, very much in need of
> more features and planning, most likely full of bugs, and it hasn't had any
> work done to allow external reuse of modules, interfacing, APIs etc.
>
> See [todo.md](todo.md) for a general roadmap on the project (periodically
> updated)

osuvs makes use of the
[Plackett-Luce model](https://jmlr.csail.mit.edu/papers/volume12/weng11a/weng11a.pdf)
implementation provided by the [openskill](https://pypi.org/project/openskill/)
Python package.

Currently, only manually selected, 1v1 matches are supported, but any
configuration is possible in the future.

## Getting started

Requirements:

* [Discord application with a bot user](https://discord.com/developers/applications)
* [osu! oauth application](https://osu.ppy.sh/home/account/edit#oauth)
* activated [Python virtual environment](https://docs.python.org/3/library/venv.html) (optional)

### Setup

```console
$ pip install -r requirements.txt # install dependencies
...

$ python 'extra utils'/init_db.py # initialize database
Enter the names of the rating models (separated by spaces): 

$ python 'extra utils'/setup_token.py # save Discord API secret
Enter your Discord bot token: *****

$ python 'extra utils'/setup_osu_api.py # save osu! API secrets
Enter your client ID: 123456789
Enter your client secret: *****
```

### Starting the bot

```console
$ python bot.py
2024-08-18 18:47:24 INFO     discord.client logging in using static token
2024-08-18 18:47:26 INFO     discord.gateway Shard ID None has connected to Gateway (Session ID: a1ef0fb26844e08ec98848df67387fd0).
Logged in as osu-vs#5228 (ID: 1271214102458404864)
------
Got guild: verarr's discord bot factory
owo bot is here: 289066747443675143
------
Ready!
```
