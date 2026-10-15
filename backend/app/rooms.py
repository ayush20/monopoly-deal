"""Single-instance, authoritative room lifecycle and private state projection."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from enum import StrEnum

from .game import pending as pending_rules
from .game.cards import Card, CardType, Color
from .game.game import PLAYS_PER_TURN, GameState, create_game
from .game.pending import PendingAction, Stage

RESERVATION_SECONDS = 600


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
    pending: PendingAction | None = None


def card_name(card: Card) -> str:
    """Human-readable card title for the client catalog."""

    def label(color: Color) -> str:
        return color.value.replace("_", " ").title()

    if card.card_type is CardType.MONEY:
        return f"${card.value}M"
    if card.card_type is CardType.PROPERTY:
        return f"{label(next(iter(card.colors)))} Property"
    if card.card_type is CardType.PROPERTY_WILD:
        if len(card.colors) == len(Color):
            return "Wild Property (any color)"
        return "Wild " + " / ".join(sorted(label(c) for c in card.colors))
    if card.card_type is CardType.RENT:
        if len(card.colors) == len(Color):
            return "Rent (any color)"
        return "Rent " + " / ".join(sorted(label(c) for c in card.colors))
    assert card.action is not None
    return card.action.value.replace("_", " ").title()


def card_entry(card: Card) -> dict[str, object]:
    return {
        "id": card.id,
        "name": card_name(card),
        "type": card.card_type.value,
        "value": card.value,
        "colors": sorted(color.value for color in card.colors),
        "action": card.action.value if card.action else None,
    }


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
        away = member.disconnected_at
        if away is not None and time.monotonic() - away > RESERVATION_SECONDS:
            raise RoomError("The reconnect reservation has expired.")
        member.connected, member.socket_id, member.disconnected_at = True, socket_id, None
        return room, member

    def member_for_socket(self, socket_id: str) -> tuple[Room, Member] | None:
        for room in self.rooms.values():
            for member in room.members:
                if member.socket_id == socket_id and not member.removed:
                    return room, member
        return None

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

    # ---- gameplay commands -------------------------------------------------

    def start_turn(self, room: Room, member: Member) -> None:
        self._play_guard(room, member).start_turn(member.id)

    def bank(self, room: Room, member: Member, card_id: str) -> None:
        self._play_guard(room, member).bank_card(member.id, card_id)

    def play_property(self, room: Room, member: Member, card_id: str, color: Color) -> None:
        game = self._play_guard(room, member)
        game.play_property(member.id, card_id, color)
        self._sync(room)

    def move_wild(self, room: Room, member: Member, card_id: str, color: Color) -> None:
        game = self._play_guard(room, member)
        game.move_wild_property(member.id, card_id, color)
        self._sync(room)

    def improve(self, room: Room, member: Member, card_id: str, color: Color) -> None:
        self._play_guard(room, member).play_improvement(member.id, card_id, color)

    def pass_go(self, room: Room, member: Member, card_id: str) -> None:
        self._play_guard(room, member).play_pass_go(member.id, card_id)

    def discard(self, room: Room, member: Member, card_ids: list[str]) -> None:
        self._play_guard(room, member).discard_to_limit(member.id, card_ids)

    def end_turn(self, room: Room, member: Member) -> None:
        self._play_guard(room, member).end_turn(member.id)

    def action(self, room: Room, member: Member, card_id: str, params: dict[str, str]) -> None:
        game = self._play_guard(room, member)
        pending = pending_rules.create_pending(game, member.id, card_id, params)
        room.pending = pending

    def respond(self, room: Room, member: Member, accept: bool, card_id: str | None = None) -> None:
        game, pending = self._pending_guard(room, member)
        if accept:
            done = pending_rules.accept(game, pending, member.id)
        elif card_id:
            pending_rules.play_just_say_no(game, pending, member.id, card_id)
            return
        else:
            raise RoomError("Choose accept or a Just Say No card.")
        self._after_pending_step(room, done)

    def pay(self, room: Room, member: Member, card_ids: list[str]) -> None:
        game, pending = self._pending_guard(room, member)
        done = pending_rules.pay(game, pending, member.id, card_ids)
        self._after_pending_step(room, done)

    def _after_pending_step(self, room: Room, done: bool) -> None:
        if done:
            room.pending = None
        self._sync(room)

    def _sync(self, room: Room) -> None:
        """End the room as soon as the engine reports a winner."""
        if room.game is not None and room.game.winner_id is not None:
            room.status = RoomStatus.ENDED
            room.pending = None

    def _game(self, room: Room, member: Member) -> GameState:
        if room.game is None or room.status is RoomStatus.LOBBY:
            raise RoomError("The game has not started.")
        if room.status is RoomStatus.PAUSED:
            raise RoomError("The game is paused.")
        if room.status is not RoomStatus.IN_PROGRESS or room.game.winner_id is not None:
            raise RoomError("The game is over.")
        if member.removed or not member.active:
            raise RoomError("You are not playing in this game.")
        return room.game

    def _play_guard(self, room: Room, member: Member) -> GameState:
        game = self._game(room, member)
        if room.pending is not None:
            raise RoomError("Finish the pending action first.")
        return game

    def _pending_guard(self, room: Room, member: Member) -> tuple[GameState, PendingAction]:
        game = self._game(room, member)
        if room.pending is None:
            raise RoomError("There is nothing to respond to.")
        return game, room.pending

    # ---- projection --------------------------------------------------------

    def view(self, room: Room, viewer: Member) -> dict[str, object]:
        """Project only the viewer's hand; all other hands remain absent."""
        game = room.game
        players: list[dict[str, object]] = []
        now = time.monotonic()
        for member in room.members:
            entry: dict[str, object] = {
                "id": member.id,
                "name": member.name,
                "host": member.is_host,
                "ready": member.ready,
                "active": member.active,
                "connected": member.connected,
                "removed": member.removed,
                "reservationSeconds": (
                    max(0, int(RESERVATION_SECONDS - (now - member.disconnected_at)))
                    if member.disconnected_at is not None
                    else None
                ),
            }
            if game is not None:
                game_player = next((item for item in game.players if item.id == member.id), None)
                if game_player is not None:
                    entry["bank"] = list(game_player.bank)
                    entry["properties"] = {
                        color.value: list(cards) for color, cards in game_player.properties.items()
                    }
                    entry["improvements"] = {
                        color.value: list(cards)
                        for color, cards in game_player.improvements.items()
                        if cards
                    }
                    entry["handCount"] = len(game_player.hand)
                    entry["completedSets"] = game.completed_set_count(member.id)
                    if member.id == viewer.id:
                        entry["hand"] = list(game_player.hand)
            players.append(entry)
        view: dict[str, object] = {
            "code": room.code,
            "status": room.status,
            "you": viewer.id,
            "players": players,
            "turn": None,
            "drawCount": None,
            "discardTop": None,
            "discardCount": None,
            "pending": None,
            "winner": None,
            "cards": {},
        }
        if game is not None:
            view["turn"] = {
                "playerId": game.current_player.id,
                "phase": game.phase.value,
                "playsUsed": game.actions_played,
                "playsMax": PLAYS_PER_TURN,
            }
            view["drawCount"] = len(game.draw_pile)
            view["discardTop"] = game.discard_pile[-1] if game.discard_pile else None
            view["discardCount"] = len(game.discard_pile)
            view["winner"] = game.winner_id
            view["cards"] = {card_id: card_entry(card) for card_id, card in game.cards.items()}
            if room.pending is not None and room.pending.involves(viewer.id):
                view["pending"] = self._pending_view(room.pending, game)
        return view

    def _pending_view(self, pending: PendingAction, game: GameState) -> dict[str, object]:
        window = pending.resolution.window if pending.resolution else None
        debt = pending_rules.current_obligation(pending)
        return {
            "kind": pending.kind,
            "stage": pending.stage.value,
            "initiatorId": pending.initiator_id,
            "cardIds": list(pending.card_ids),
            "targets": list(pending.targets),
            "params": dict(pending.params),
            "awaitingId": pending.awaiting_id,
            "currentTargetId": pending.current_target,
            "cancelled": bool(window and window.cancelled)
            if pending.stage is Stage.RESPONSE
            else False,
            "payment": {
                "payerId": debt.payer_id,
                "recipientId": debt.recipient_id,
                "amount": debt.amount,
                "reason": debt.reason,
                "queue": [
                    {"payerId": item.payer_id, "amount": item.amount}
                    for item in (pending.payments.obligations if pending.payments else [])
                ],
            }
            if debt is not None
            else None,
        }

    def _remove(self, room: Room, target_id: str) -> None:
        target = next(
            (member for member in room.members if member.id == target_id and not member.removed),
            None,
        )
        if target is None:
            raise RoomError("The player cannot be removed.")
        target.removed, target.active, target.connected = True, False, False
        target.ready = False
        if room.pending is not None and room.pending.involves(target_id):
            room.pending = None
        if room.game is not None:
            room.game.remove_player(target_id)
            if len(room.game.players) == 1:
                room.game.winner_id = room.game.players[0].id
                room.status = RoomStatus.ENDED
                room.pending = None

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
