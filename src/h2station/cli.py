"""Command-line entry point for the local monitoring service."""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrogen station dynamic simulator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    uvicorn.run(
        "h2station.api:app",
        host=arguments.host,
        port=arguments.port,
    )
