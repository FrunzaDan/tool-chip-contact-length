from random_color import MAX_CHANNEL_VALUE, MIN_CHANNEL_VALUE, random_line_color


def test_random_line_color_channels_are_within_configured_range():
    for _ in range(50):
        blue, green, red = random_line_color()
        for channel in (blue, green, red):
            assert MIN_CHANNEL_VALUE <= channel <= MAX_CHANNEL_VALUE
