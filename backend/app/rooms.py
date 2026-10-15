"""Single-instance, authoritative room lifecycle and private state projection."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from enum import StrEnum

from .game.game import GameState, create_game


class RoomError(ValueError):
    """A client-safe room command rejection."""


class RoomStatus(StrEnum):
    LOBBY = "lobby"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass(slots=True)
class Member:
    id: str
    token: str
    name: str
    is_host: bool = False
    ready: bool = False
    active: bool = False
    connected: bool = True
    socket_id: str | None = None
    disconnected_at: float | None = None
    removed: bool = False


@dataclass(slots=True)
class Room:
    code: str
    members: list[Member]
    status: RoomStatus = RoomStatus.LOBBY
    game: GameState | None = None


class RoomService:
    """In-memory rooms for one persistent backend process."""

    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def create_room(self, name: str, socket_id: str | None = None) -> tuple[Room, Member]:
        member = self._member(name, socket_id, host=True)
        room = Room(code=self._new_code(), members=[member])
        self.rooms[room.code] = room
        return room, member

    def join_room(self, code: str, name: str, socket_id: str | None = None) -> tuple[Room, Member]:
        room = self._room(code)
        if room.status is RoomStatus.ENDED:
            raise RoomError("This room has ended.")
        if len([member for member in room.members if not member.removed]) >= 5:
            raise RoomError("This room is full.")
        member = self._member(name, socket_id)
        room.members.append(member)
        return room, member

    def reconnect(self, code: str, token: str, socket_id: str | None = None) -> tuple[Room, Member]:
        room = self._room(code)
        member = next(
            (item for item in room.members if item.token == token and not item.removed), None
        )
        if member is None:
            raise RoomError("The reconnect token is invalid.")
        if member.disconnected_at is not None and time.monotonic() - member.disconnected_at > 600:
            raise RoomError("The reconnect reservation has expired.")
        member.connected, member.socket_id, member.disconnected_at = True, socket_id, None
        return room, member

    def set_ready(self, room: Room, member: Member, ready: bool) -> None:
        if room.status is not RoomStatus.LOBBY:
            raise RoomError("Readiness can only change in the lobby.")
        member.ready = ready

    def start(self, room: Room, host: Member) -> None:
        self._host(room, host)
        if room.status is not RoomStatus.LOBBY:
            raise RoomError("Only a lobby game can start.")
        participants = [member for member in room.members if member.ready and not member.removed]
        if not 2 <= len(participants) <= 5:
            raise RoomError("At least two ready players are required.")
        room.game = create_game([member.id for member in participants])
        for member in room.members:
            member.active = member in participants
        room.status = RoomStatus.IN_PROGRESS

    def host_control(
        self, room: Room, host: Member, command: str, target_id: str | None = None
    ) -> None:
        self._host(room, host)
        if command == "pause" and room.status is RoomStatus.IN_PROGRESS:
            room.status = RoomStatus.PAUSED
        elif command == "resume" and room.status is RoomStatus.PAUSED:
            room.status = RoomStatus.IN_PROGRESS
        elif command == "end":
            room.status = RoomStatus.ENDED
        elif command == "remove" and target_id is not None:
            self._remove(room, target_id)
        else:
            raise RoomError("That host control is not available now.")

    def disconnect(self, socket_id: str) -> Room | None:
        for room in self.rooms.values():
            member = next((item for item in room.members if item.socket_id == socket_id), None)
            if member is None:
                continue
            member.connected, member.socket_id, member.disconnected_at = (
                False,
                None,
                time.monotonic(),
            )
            if member.active and room.status is RoomStatus.IN_PROGRESS:
                room.status = RoomStatus.PAUSED
            return room
        return None

    def view(self, room: Room, viewer: Member) -> dict[str, object]:
        """Project only the viewer's hand; all other hands remain absent."""
        players: list[dict[str, object]] = []
        for member in room.members:
            entry: dict[str, object] = {
                "id": member.id,
                "name": member.name,
                "host": member.is_host,
                "ready": member.ready,
                "active": member.active,
                "connected": member.connected,
                "removed": member.removed,
            }
            if room.game is not None:
                game_player = next(
                    (item for item in room.game.players if item.id == member.id), None
                )
                if game_player is not None:
                    entry["bank"] = list(game_player.bank)
                    entry["properties"] = {
                        color.value: list(cards) for color, cards in game_player.properties.items()
                    }
                    if member.id == viewer.id:
                        entry["hand"] = list(game_player.hand)
            players.append(entry)
        return {"code": room.code, "status": room.status, "players": players}

    def _remove(self, room: Room, target_id: str) -> None:
        target = next(
            (member for member in room.members if member.id == target_id and not member.removed),
            None,
        )
        if target is None:
            raise RoomError("The player cannot be removed.")
        target.removed, target.active, target.connected = True, False, False
        if room.game is not None:
            room.game.players = [player for player in room.game.players if player.id != target_id]
            if len(room.game.players) == 1:
                room.game.winner_id = room.game.players[0].id
                room.status = RoomStatus.ENDED

    def _room(self, code: str) -> Room:
        room = self.rooms.get(code.upper())
        if room is None:
            raise RoomError("Room code not found.")
        return room

    def _host(self, room: Room, member: Member) -> None:
        if not member.is_host:
            raise RoomError("Only the host can do that.")

    def _member(self, name: str, socket_id: str | None, host: bool = False) -> Member:
        clean_name = name.strip()
        if not 1 <= len(clean_name) <= 24:
            raise RoomError("Display names must be 1 to 24 characters.")
        return Member(
            secrets.token_hex(8), secrets.token_urlsafe(24), clean_name, host, socket_id=socket_id
        )

    def _new_code(self) -> str:
        while True:
            code = secrets.token_hex(3).upper()
            if code not in self.rooms:
                return code
