from h2station.api import _frames_after_cursor


def _frames(count: int, start: int = 0):
    return [{"sequence": sequence, "time_s": float(sequence)}
            for sequence in range(start, start + count)]


def test_frame_cursor_reads_only_new_tail_frames():
    frames = _frames(10)

    assert _frames_after_cursor(frames, 7) == frames[8:]
    assert _frames_after_cursor(frames, 9) == []


def test_frame_cursor_catches_up_when_history_was_trimmed():
    frames = _frames(4, start=20)

    assert _frames_after_cursor(frames, 2) == frames

