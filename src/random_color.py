"""Random annotation colors."""

import random

# Range for each color channel (kept bright so lines stand out on dark images)
MIN_CHANNEL_VALUE = 120
MAX_CHANNEL_VALUE = 255


def random_line_color() -> tuple[int, int, int]:
    """Return a random BGR color (OpenCV's channel order) in the configured range."""
    blue = random.randint(MIN_CHANNEL_VALUE, MAX_CHANNEL_VALUE)
    green = random.randint(MIN_CHANNEL_VALUE, MAX_CHANNEL_VALUE)
    red = random.randint(MIN_CHANNEL_VALUE, MAX_CHANNEL_VALUE)
    return blue, green, red
