"""Unreal-specific, read-only API; independent of the three assistant APIs."""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Callable, Any
from urllib.parse import urlsplit
from threading import Lock

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .visualization import build_snapshot, scene_manifest


class RendererBinding(BaseModel):
    run_id: str | None = Field(default=None, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    request_serial: int | None = Field(default=None, ge=0, le=9007199254740991, strict=True)


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
