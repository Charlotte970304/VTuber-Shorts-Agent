from vtuber_shorts_agent.srt import format_srt_time, to_srt


def test_long_livestream_timestamp():
    assert format_srt_time(4 * 3600 + 3 * 60 + 2.345) == "04:03:02,345"


def test_japanese_srt():
    result = to_srt([{"start": 1.25, "end": 3.5, "text": "こんにちは！"}])
    assert "00:00:01,250 --> 00:00:03,500" in result
    assert "こんにちは！" in result
