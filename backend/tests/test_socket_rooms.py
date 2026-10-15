from app import create_app, socketio


def test_socket_room_create_join_and_private_views() -> None:
    app = create_app({"TESTING": True})
    host = socketio.test_client(app)
    guest = socketio.test_client(app)

    created = host.emit("room:create", {"name": "Ada"}, callback=True)
    code = created["state"]["code"]
    joined = guest.emit("room:join", {"name": "Bert", "code": code}, callback=True)

    assert "token" in created and "token" in joined
    assert len(joined["state"]["players"]) == 2
    host.disconnect()
    guest.disconnect()


def test_socket_rejects_invalid_room_code() -> None:
    app = create_app({"TESTING": True})
    client = socketio.test_client(app)

    result = client.emit("room:join", {"name": "Ada", "code": "NOPE"}, callback=True)

    assert result == {"error": "Room code not found."}
    client.disconnect()
