"""Flask application factory for the Deal Room realtime service."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any, cast

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

from .game.cards import Color
from .game.errors import GameRuleError
from .rooms import Member, Room, RoomError, RoomService

socketio = SocketIO(async_mode="threading")


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create the HTTP and Socket.IO application without gameplay state."""
    load_dotenv()
    app = Flask(__name__)
    origins = [
        origin.strip()
        for origin in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5174").split(",")
        if origin.strip()
    ]
    # origins = ["*"]
    app.config["ALLOWED_ORIGINS"] = origins

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-change-me"),
        # ALLOWED_ORIGINS=origins,
        # ALLOWED_ORIGINS=os.environ.get("ALLOWED_ORIGINS", "http://localhost:5174"),
    )
    if test_config is not None:
        app.config.update(test_config)

    CORS(app, resources={r"/*": {"origins": origins}})
    socketio.init_app(app, cors_allowed_origins=origins)
    rooms = RoomService()
    app.extensions["rooms"] = rooms

    @app.get("/health")
    def health() -> tuple[Any, int]:
        return jsonify({"service": "deal-room-api", "status": "ok"}), 200

    @socketio.on("health:ping")
    def health_ping(payload: dict[str, Any] | None = None) -> dict[str, str]:
        """Provide a minimal unauthenticated Socket.IO connectivity check."""
        del payload
        return {"status": "ok", "service": "deal-room-api"}

    lock = threading.RLock()

    def socket_id() -> str:
        return cast(str, getattr(request, "sid"))

    def broadcast(room: Room) -> None:
        """Send each connected member their own private projection of the room."""
        for member in room.members:
            if member.socket_id and member.connected and not member.removed:
                socketio.emit("room:state", rooms.view(room, member), to=member.socket_id)

    def text(payload: Any, key: str) -> str:
        value = payload.get(key) if isinstance(payload, dict) else None
        if not isinstance(value, str) or not value:
            raise RoomError(f"Missing required field: {key}.")
        return value

    def color(payload: Any, key: str = "color") -> Color:
        try:
            return Color(text(payload, key))
        except ValueError:
            raise RoomError("Unknown color.") from None

    def caller() -> tuple[Room, Member]:
        found = rooms.member_for_socket(socket_id())
        if found is None:
            raise RoomError("You are not in a room.")
        return found

    Handler = Callable[[Room, Member, Any], dict[str, object] | None]

    def command(event: str) -> Callable[[Handler], Handler]:
        """Register a member command: resolve caller, run, broadcast, ack ok/error."""

        def register(handler: Handler) -> Handler:
            @socketio.on(event)
            def wrapper(payload: Any = None) -> dict[str, object]:
                with lock:
                    try:
                        room, member = caller()
                        extra = handler(room, member, payload) or {}
                        broadcast(room)
                        return {"ok": True, **extra}
                    except (RoomError, GameRuleError) as error:
                        return {"error": str(error)}

            return handler

        return register

    def joined(room: Room, member: Member) -> dict[str, object]:
        broadcast(room)
        return {"ok": True, "token": member.token, "state": rooms.view(room, member)}

    @socketio.on("room:create")
    def room_create(payload: Any = None) -> dict[str, object]:
        with lock:
            try:
                room, member = rooms.create_room(
                    payload.get("name", "") if isinstance(payload, dict) else "", socket_id()
                )
                return joined(room, member)
            except RoomError as error:
                return {"error": str(error)}

    @socketio.on("room:join")
    def room_join(payload: Any = None) -> dict[str, object]:
        with lock:
            try:
                data = payload if isinstance(payload, dict) else {}
                room, member = rooms.join_room(
                    str(data.get("code", "")), str(data.get("name", "")), socket_id()
                )
                return joined(room, member)
            except RoomError as error:
                return {"error": str(error)}

    @socketio.on("room:reconnect")
    def room_reconnect(payload: Any = None) -> dict[str, object]:
        with lock:
            try:
                room, member = rooms.reconnect(
                    text(payload, "code"), text(payload, "token"), socket_id()
                )
                return joined(room, member)
            except RoomError as error:
                return {"error": str(error)}

    @socketio.on("disconnect")
    def room_disconnect() -> None:
        with lock:
            room = rooms.disconnect(socket_id())
            if room is not None:
                broadcast(room)

    @command("room:ready")
    def room_ready(room: Room, member: Member, payload: Any) -> None:
        ready = payload.get("ready", True) if isinstance(payload, dict) else True
        rooms.set_ready(room, member, bool(ready))

    @command("room:start")
    def room_start(room: Room, member: Member, payload: Any) -> None:
        rooms.start(room, member)

    for name in ("pause", "resume", "end"):

        def host_command(room: Room, member: Member, payload: Any, name: str = name) -> None:
            rooms.host_control(room, member, name)

        command(f"room:{name}")(host_command)

    @command("room:remove")
    def room_remove(room: Room, member: Member, payload: Any) -> None:
        rooms.host_control(room, member, "remove", text(payload, "targetId"))

    @command("game:start_turn")
    def game_start_turn(room: Room, member: Member, payload: Any) -> None:
        rooms.start_turn(room, member)

    @command("game:bank")
    def game_bank(room: Room, member: Member, payload: Any) -> None:
        rooms.bank(room, member, text(payload, "cardId"))

    @command("game:play_property")
    def game_play_property(room: Room, member: Member, payload: Any) -> None:
        rooms.play_property(room, member, text(payload, "cardId"), color(payload))

    @command("game:move_wild")
    def game_move_wild(room: Room, member: Member, payload: Any) -> None:
        rooms.move_wild(room, member, text(payload, "cardId"), color(payload))

    @command("game:improve")
    def game_improve(room: Room, member: Member, payload: Any) -> None:
        rooms.improve(room, member, text(payload, "cardId"), color(payload))

    @command("game:pass_go")
    def game_pass_go(room: Room, member: Member, payload: Any) -> None:
        rooms.pass_go(room, member, text(payload, "cardId"))

    @command("game:action")
    def game_action(room: Room, member: Member, payload: Any) -> None:
        card_id = text(payload, "cardId")
        params = {k: v for k, v in payload.items() if k != "cardId" and isinstance(v, str)}
        rooms.action(room, member, card_id, params)

    @command("game:respond")
    def game_respond(room: Room, member: Member, payload: Any) -> None:
        kind = text(payload, "response")
        if kind == "accept":
            rooms.respond(room, member, True)
        elif kind == "just_say_no":
            rooms.respond(room, member, False, text(payload, "cardId"))
        else:
            raise RoomError("Response must be accept or just_say_no.")

    @command("game:pay")
    def game_pay(room: Room, member: Member, payload: Any) -> None:
        ids = payload.get("cardIds") if isinstance(payload, dict) else None
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            raise RoomError("cardIds must be a list of card ids.")
        rooms.pay(room, member, ids)

    @command("game:discard")
    def game_discard(room: Room, member: Member, payload: Any) -> None:
        ids = payload.get("cardIds") if isinstance(payload, dict) else None
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            raise RoomError("cardIds must be a list of card ids.")
        rooms.discard(room, member, ids)

    @command("game:end_turn")
    def game_end_turn(room: Room, member: Member, payload: Any) -> None:
        rooms.end_turn(room, member)

    return app
