from __future__ import annotations

from collections.abc import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_socketio import SocketIOTestClient

from app import create_app, socketio


@pytest.fixture()
def app() -> Generator[Flask, None, None]:
    application = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
    yield application


def test_health_endpoint(app: Flask) -> None:
    client: FlaskClient = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"service": "deal-room-api", "status": "ok"}


def test_socket_health_ping(app: Flask) -> None:
    client: SocketIOTestClient = socketio.test_client(app)

    response = client.emit("health:ping", {"source": "test"}, callback=True)

    assert response == {"service": "deal-room-api", "status": "ok"}
    client.disconnect()
