from h2station.api import (
    _frames_after_cursor,
    _risk_zone_state_signature,
    _stream_display_frames,
)


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


def test_risk_zone_signature_invalidates_on_safety_state_changes_only():
    frame = {
        "time_s": 12.0,
        "esd": False,
        "active_faults": [],
        "total_leak_flow_g_s": 0.0,
        "hazop": {"active": [], "releases": []},
        "process_operations": {"relief_open": {}},
    }

    same = dict(frame, time_s=13.0)
    esd = dict(frame, esd=True)

    assert _risk_zone_state_signature(frame) == _risk_zone_state_signature(same)
    assert _risk_zone_state_signature(frame) != _risk_zone_state_signature(esd)


def test_live_stream_coalesces_quiet_frames_but_keeps_transitions():
    frames = []
    for sequence in range(6):
        frames.append({
            "sequence": sequence,
            "esd": sequence >= 3,
            "active_faults": ["hydrogen-leak:cascade.high"] if sequence >= 3 else [],
            "relief_valves_open": [],
            "dispatch_bank": "low",
            "dispatch_bank_2": None,
            "recharge_bank": None,
            "analysis": {"status": "CRITICAL" if sequence >= 3 else "NORMAL"},
            "process_activity": {},
        })

    selected = _stream_display_frames(frames)

    assert [frame["sequence"] for frame in selected] == [0, 3, 5]
