# Bounded, gradual cursor-centered wheel zoom

Date: 2026-09-19

## User report

Wheel zoom was excessively abrupt and reached its limit too quickly.

## Changes

- OrbitControls zoom speed reduced to 0.45.
- Native zoom-to-cursor enabled, rather than always zooming toward the fixed overview center.
- Minimum camera-target distance lowered from 3 to 1.2 scene units for closer equipment inspection.
- Wheel line/page units are normalized to pixels.
- Each incoming wheel delta is bounded to +/-120, with an outstanding input bound of +/-480.
- Bounded wheel input is distributed over rendered frames and forwarded to the existing OrbitControls wheel handler.
- Forwarded events are marked in a WeakSet to prevent interception recursion.
- Wheel input cancels camera-preset transitions, preserving direct user control.

## Scope

The bundled OrbitControls source was consulted for zoomSpeed, zoomToCursor and wheel-delta normalization. The library itself is unchanged. Touch gestures, drag orbit, equipment focus, physics and API remain unchanged.

This is an input-handling adjustment, not a measured interaction-quality claim. No execution, tests, browser inspection or validation were performed. The recurring enhancement automation remains paused.
