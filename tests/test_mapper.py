"""Basic test for exercise mapper."""

from hevy2garmin.mapper import lookup_exercise, HEVY_TO_GARMIN


def test_known_exercise():
    cat, subcat, name = lookup_exercise("Bench Press (Barbell)")
    assert cat == 0
    assert subcat == 1
    assert name == "Bench Press (Barbell)"


def test_unknown_exercise():
    cat, subcat, name = lookup_exercise("Made Up Exercise 12345")
    assert cat == 65534  # UNKNOWN
    assert name == "Made Up Exercise 12345"


def test_mapping_count():
    assert len(HEVY_TO_GARMIN) >= 400
