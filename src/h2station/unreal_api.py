"""Unreal-specific, read-only API; independent of the three assistant APIs."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
import os
import time
from typing import Callable, Any, Literal
from urllib.parse import urlsplit
from threading import Lock

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .visualization import build_snapshot, scene_manifest


class RendererBinding(BaseModel):
    run_id: str | None = Field(default=None, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    request_serial: int | None = Field(default=None, ge=0, le=9007199254740991, strict=True)


class EquipmentDisplay(BaseModel):
    component_id: str = Field(max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    pressure_mpa: float | None = None
    temperature_c: float | None = None
    mass_kg: float | None = None
    flow_g_s: float | None = None


class RendererVisualState(BaseModel):
    """Visual state read back from components after a snapshot was applied."""

    show_risk: bool = False
    show_distance: bool = False
    show_cameras: bool = False
    show_detectors: bool = False
    risk_mode: Literal["relative", "absolute"] = "relative"
    selected_equipment: str = Field(default="", max_length=80, pattern=r"^[a-zA-Z0-9_.-]*$")
    hose_1_mode: Literal["parked", "connected", "invalid"] = "invalid"
    hose_2_mode: Literal["parked", "connected", "invalid"] = "invalid"
    visible_jets: list[str] = Field(default_factory=list, max_length=64)
    visible_distances: list[str] = Field(default_factory=list, max_length=64)
    visible_distance_labels: list[str] = Field(default_factory=list, max_length=64)
    visible_risk_components: list[str] = Field(default_factory=list, max_length=64)
    visible_fire_components: list[str] = Field(default_factory=list, max_length=64)
    visible_highlight_components: list[str] = Field(default_factory=list, max_length=64)
    visible_cameras: list[str] = Field(default_factory=list, max_length=16)
    visible_detectors: list[str] = Field(default_factory=list, max_length=64)
    visible_auxiliary: list[str] = Field(default_factory=list, max_length=64)
    personnel_at_muster: list[str] = Field(default_factory=list, max_length=16)
    valve_states: dict[str, Literal["open", "closed", "moving", "failed", "unknown"]] = Field(
        default_factory=dict, max_length=64
    )
    auxiliary_states: dict[str, str] = Field(default_factory=dict, max_length=128)
    recovery_completed: int = Field(default=0, ge=0, le=64)
    recovery_total: int = Field(default=0, ge=0, le=64)


class RendererFeedback(BaseModel):
    run_id: str = Field(max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    generation: int = Field(ge=0, le=2147483647, strict=True)
    sequence: int = Field(ge=-1, le=9007199254740991, strict=True)
    equipment: list[EquipmentDisplay] = Field(max_length=64)
    visual_state: RendererVisualState | None = None


def terminal(status: str) -> bool:
    return status in ("complete", "failed", "cancelled", "stopped")


def make_unreal_router(read_state: Callable[[str], tuple[dict, dict | None, dict | None, dict | None]]) -> APIRouter:
    router = APIRouter(tags=["Unreal visualization"])
    sessions: dict[str, dict[str, Any]] = {}
    session_lock = Lock()

    @router.get("/api/integrations/unreal/session/{renderer_id}")
    def binding(renderer_id: str) -> dict[str, Any]:
        with session_lock:
            return dict(sessions.get(renderer_id, {"run_id": None, "generation": 0}))

    @router.post("/api/integrations/unreal/session/{renderer_id}")
    def bind(renderer_id: str, request: RendererBinding) -> dict[str, Any]:
        if not renderer_id.isascii() or not renderer_id.replace("-", "").replace("_", "").isalnum() or len(renderer_id) > 64:
            raise HTTPException(422, "Invalid renderer id")
        if request.run_id is not None:
            read_state(request.run_id)  # No binding to an unknown run.
        with session_lock:
            if renderer_id not in sessions and len(sessions) >= 64:
                raise HTTPException(429, "Renderer session limit reached")
            old = sessions.get(renderer_id, {"run_id": None, "generation": 0})
            serial = request.request_serial
            if serial is not None and serial < old.get("request_serial", -1):
                raise HTTPException(409, "Stale renderer binding request")
            if serial is not None and serial == old.get("request_serial") and old["run_id"] != request.run_id:
                raise HTTPException(409, "Conflicting renderer binding request")
            if old["run_id"] != request.run_id:
                old = {"run_id": request.run_id, "generation": old["generation"] + 1}
            if serial is not None:
                old = {**old, "request_serial": serial}
            sessions[renderer_id] = old
            return dict(old)

    @router.get("/api/integrations/unreal/session/{renderer_id}/feedback")
    def get_feedback(renderer_id: str) -> dict[str, Any]:
        with session_lock:
            session = sessions.get(renderer_id)
            if not session or "feedback" not in session:
                raise HTTPException(404, "No renderer feedback")
            return dict(session["feedback"])

    @router.post("/api/integrations/unreal/session/{renderer_id}/feedback")
    def record_feedback(renderer_id: str, request: RendererFeedback) -> dict[str, Any]:
        if not renderer_id.isascii() or not renderer_id.replace("-", "").replace("_", "").isalnum() or len(renderer_id) > 64:
            raise HTTPException(422, "Invalid renderer id")
        # Reject non-finite renderer telemetry here rather than in Pydantic's
        # validation handler. Some JSON clients accept NaN/Infinity even
        # though JSON does not; keeping those values out of the validation
        # error payload guarantees that the 422 response is itself valid JSON.
        for equipment in request.equipment:
            for field in ("pressure_mpa", "temperature_c", "mass_kg", "flow_g_s"):
                value = getattr(equipment, field)
                if value is not None and not math.isfinite(value):
                    raise HTTPException(422, "Displayed values must be finite or null")
        job, frame, safety, risk = read_state(request.run_id)
        current_sequence = int((frame or {}).get("sequence", -1))
        if request.sequence > current_sequence:
            raise HTTPException(409, "Renderer feedback is ahead of the server frame")
        with session_lock:
            session = sessions.get(renderer_id)
            if (not session or session.get("run_id") != request.run_id
                    or session.get("generation") != request.generation):
                raise HTTPException(409, "Renderer feedback does not match the active binding")
            previous = session.get("feedback") or {}
            if request.sequence < int(previous.get("sequence", -1)):
                raise HTTPException(409, "Stale renderer feedback")
            parity: dict[str, Any] = {"status": "superseded", "matches": None, "mismatches": []}
            if request.sequence == current_sequence:
                server = build_snapshot(request.run_id, job, frame, safety, risk)
                expected = {row["component_id"]: row for row in server["equipment"]}
                received = {row.component_id: row.model_dump() for row in request.equipment}
                mismatches = []
                for component_id in sorted(set(expected) | set(received)):
                    if component_id not in expected or component_id not in received:
                        mismatches.append({"component_id": component_id, "field": "presence"})
                        continue
                    for field in ("pressure_mpa", "temperature_c", "mass_kg", "flow_g_s"):
                        left, right = expected[component_id].get(field), received[component_id].get(field)
                        if left is None or right is None:
                            equal = left is None and right is None
                        else:
                            equal = math.isclose(float(left), float(right), rel_tol=1e-7, abs_tol=1e-7)
                        if not equal:
                            mismatches.append({"component_id": component_id, "field": field,
                                               "server": left, "renderer": right})
                parity = {"status": "compared", "matches": not mismatches,
                          "mismatches": mismatches[:64]}
            feedback = {**request.model_dump(), "received_at": datetime.now(timezone.utc).isoformat(),
                        "parity": parity}
            session["feedback"] = feedback
            return dict(feedback)

    @router.get("/api/integrations/unreal/config")
    def config() -> dict[str, Any]:
        player_url = os.environ.get("H2STATION_UNREAL_PLAYER_URL", "").strip()
        parts = urlsplit(player_url)
        if player_url and (parts.scheme not in ("http", "https") or not parts.netloc or parts.username or parts.password):
            raise HTTPException(503, "Unreal player URL must be an HTTP(S) URL without credentials")
        return {"schema_version": 1, "player_url": player_url or None,
                "configured": bool(player_url), "renderer": "unreal",
                "stream_interval_s": .1, "heartbeat_interval_s": 1.0,
                "command_endpoint": "/api/simulations/{run_id}/safety/actions",
                "command_semantics": "accepted_is_not_confirmed"}

    @router.get("/api/integrations/unreal/scene")
    def scene() -> dict[str, Any]:
        return scene_manifest()

    def snapshot(job_id: str) -> dict[str, Any]:
        job, frame, safety, risk = read_state(job_id)
        return build_snapshot(job_id, job, frame, safety, risk)

    @router.get("/api/simulations/{job_id}/visualization/snapshot")
    def get_snapshot(job_id: str) -> dict[str, Any]:
        return snapshot(job_id)

    @router.websocket("/api/simulations/{job_id}/visualization/stream")
    async def stream(websocket: WebSocket, job_id: str) -> None:
        await websocket.accept()
        last_signature = None
        last_send = 0.0
        try:
            while True:
                try:
                    state = snapshot(job_id)
                except HTTPException as exc:
                    await websocket.send_json({"type": "error", "detail": exc.detail})
                    await websocket.close(code=4404)
                    return
                # Commands can change feedback before a new process frame exists.
                # Preserve these changes and send heartbeats while simulation is paused.
                signature = json.dumps({key: value for key, value in state.items()
                                        if key != "produced_at"}, sort_keys=True, default=str)
                now = time.monotonic()
                if signature != last_signature or now - last_send >= 1.0:
                    await websocket.send_json({"type": "snapshot", "snapshot": state})
                    last_signature, last_send = signature, now
                if terminal(state["status"]):
                    await websocket.close(code=1000)
                    return
                await asyncio.sleep(.1)
        except WebSocketDisconnect:
            return

    return router
