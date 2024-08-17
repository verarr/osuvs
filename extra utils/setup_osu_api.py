import pickle

from pwinput import pwinput

details: dict[str, int | str] = {
    "client_id": int(input("Enter your client ID: ")),
    "client_secret": pwinput("Enter your client secret: "),
}

with open("osu_api.pickle", "wb") as f:
    pickle.dump(details, f)
