"""Flask application factory for the Deal Room realtime service."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_socketio import SocketIO

socketio = SocketIO(async_mode="threading")


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create the HTTP and Socket.IO application without gameplay state."""
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-change-me"),
        ALLOWED_ORIGINS=os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173"),
    )
    if test_config is not None:
        app.config.update(test_config)

    socketio.init_app(app, cors_allowed_origins=app.config["ALLOWED_ORIGINS"])

    @app.get("/health")
    def health() -> tuple[Any, int]:
        return jsonify({"service": "deal-room-api", "status": "ok"}), 200

    @socketio.on("health:ping")
    def health_ping(payload: dict[str, Any] | None = None) -> dict[str, str]:
        """Provide a minimal unauthenticated Socket.IO connectivity check."""
        del payload
        return {"status": "ok", "service": "deal-room-api"}

    return app
