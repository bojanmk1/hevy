"""Sync Hevy gym workouts to Garmin Connect."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("hevy2garmin")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
