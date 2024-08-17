import pickle

from pwinput import pwinput

token: str = pwinput("Enter your Discord bot token: ")

with open("token.pickle", "wb") as f:
    pickle.dump(token, f)
