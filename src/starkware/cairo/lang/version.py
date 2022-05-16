import os

with open(os.path.join(os.path.dirname(__file__), "VERSION")) as fp:
    __version__ = fp.read().strip()
