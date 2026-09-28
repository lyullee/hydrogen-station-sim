# 3D wheel zoom speed adjustment

## Change

- Increased OrbitControls wheel zoom speed from `0.45` to `0.85`.
- Retained the existing wheel-delta clamp, accumulated-delta limit, cursor-centered zoom, minimum distance and maximum distance.

## Intent

The previous protection against one-wheel-event extreme zoom remains active, while ordinary wheel movement responds about twice as strongly.

## Validation

No browser execution or interaction test was performed for this adjustment.
