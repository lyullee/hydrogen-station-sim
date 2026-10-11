# SAGA direct-stream grounding validation — 2026-10-12

The SAGA direct-answer service now has a regression test that parses the SSE
events themselves. It exercises the same display path used by the digital-twin
UI and checks every `event: token`, rather than checking only the final answer.
The provider response is buffered, the numeric evidence guard is applied, and
only then are token events emitted.

The test ran against SAGA commit
`4e1b7ca9b5c4c280717dad788c810d007c12d0e9`:

```text
..\hydrogen-station-sim\.venv\Scripts\python.exe -m pytest tests_python/test_digital_twin_direct_chat.py -q
10 passed, 0 failed, 2 warnings in 23.90 s
```

The test intentionally supplies an invented `88 MPa` value. The value is
absent from every streamed token and from the final answer event, while the
grounding notice remains present. This establishes a deterministic response
contract for the interface; it does not establish physical-model accuracy,
field safety, operator effectiveness, or expert-rated usefulness.
