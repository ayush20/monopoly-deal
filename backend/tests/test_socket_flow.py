"""End-to-end Socket.IO flow: lobby, turn, hand limit, reconnect, host controls."""

from typing import Any

from app import create_app, socketio
from app.rooms import RoomService


def _states(client: Any) -> list[dict[str, Any]]:
    return [m["args"][0] for m in client.get_received() if m["name"] == "room:state"]


def _two_players() -> tuple[Any, Any, Any, Any, Any, RoomService]:
    app = create_app({"TESTING": True})
    host, guest = socketio.test_client(app), socketio.test_client(app)
    created = host.emit("room:create", {"name": "Ada"}, callback=True)
    code = created["state"]["code"]
    joined = guest.emit("room:join", {"name": "Bert", "code": code}, callback=True)
    return app, host, guest, created, joined, app.extensions["rooms"]


def _start(host: Any, guest: Any) -> None:
    assert host.emit("room:ready", {"ready": True}, callback=True) == {"ok": True}
    assert guest.emit("room:ready", {"ready": True}, callback=True) == {"ok": True}
    assert host.emit("room:start", {}, callback=True) == {"ok": True}


def test_lobby_broadcasts_reach_the_other_client() -> None:
    _, host, guest, created, joined, _ = _two_players()
    assert created["ok"] is True and joined["ok"] is True
    assert [len(s["players"]) for s in _states(host)][-1] == 2

    guest.emit("room:ready", {"ready": True}, callback=True)
    latest = _states(host)[-1]
    assert [p["ready"] for p in latest["players"]] == [False, True]


def test_only_host_can_start_and_needs_two_ready() -> None:
    _, host, guest, *_ = _two_players()
    assert guest.emit("room:start", {}, callback=True) == {"error": "Only the host can do that."}
    assert "error" in host.emit("room:start", {}, callback=True)
    _start(host, guest)
    states = _states(guest)
    assert states[-1]["status"] == "in_progress"
    me = next(p for p in states[-1]["players"] if p["id"] == states[-1]["you"])
    other = next(p for p in states[-1]["players"] if p["id"] != states[-1]["you"])
    assert len(me["hand"]) == 5 and "hand" not in other and other["handCount"] == 5


def test_turn_flow_bank_end_turn_and_errors() -> None:
    _, host, guest, created, joined, rooms = _two_players()
    _start(host, guest)
    room = next(iter(rooms.rooms.values()))
    assert room.game is not None
    turn_owner = room.game.current_player.id
    mine, theirs = (host, guest) if turn_owner == created["state"]["you"] else (guest, host)

    assert "error" in theirs.emit("game:start_turn", {}, callback=True)
    assert mine.emit("game:start_turn", {}, callback=True) == {"ok": True}
    state = _states(mine)[-1]
    me = next(p for p in state["players"] if p["id"] == state["you"])
    assert len(me["hand"]) == 7 and state["turn"]["phase"] == "active"

    assert "error" in mine.emit("game:bank", {}, callback=True)  # missing cardId
    assert "error" in mine.emit("game:bank", {"cardId": "nope"}, callback=True)
    assert "error" in mine.emit(
        "game:play_property", {"cardId": me["hand"][0], "color": "zz"}, callback=True
    )
    bankable = next(
        c for c in me["hand"] if state["cards"][c]["type"] in {"money", "rent", "action"}
    )
    assert mine.emit("game:bank", {"cardId": bankable}, callback=True) == {"ok": True}
    assert _states(theirs)[-1]["turn"]["playsUsed"] == 1
    assert mine.emit("game:end_turn", {}, callback=True) == {"ok": True}
    assert _states(theirs)[-1]["turn"]["phase"] == "awaiting_turn_start"
    assert room.game.current_player.id != turn_owner


def test_hand_limit_over_socket() -> None:
    _, host, guest, created, _, rooms = _two_players()
    _start(host, guest)
    room = next(iter(rooms.rooms.values()))
    assert room.game is not None
    player_id = room.game.current_player.id
    mine = host if player_id == created["state"]["you"] else guest
    mine.emit("game:start_turn", {}, callback=True)
    hand = room.game.player(player_id).hand
    hand.extend(room.game.draw_pile[:2])
    del room.game.draw_pile[:2]

    assert "Discard 2" in mine.emit("game:end_turn", {}, callback=True)["error"]
    assert mine.emit("game:discard", {"cardIds": hand[:2]}, callback=True) == {"ok": True}
    assert mine.emit("game:end_turn", {}, callback=True) == {"ok": True}


def test_commands_without_room_return_error() -> None:
    app = create_app({"TESTING": True})
    client = socketio.test_client(app)
    for event in ("room:ready", "room:start", "game:end_turn", "room:pause"):
        assert client.emit(event, {}, callback=True) == {"error": "You are not in a room."}
    assert "error" in client.emit("room:reconnect", {}, callback=True)
    assert "error" in client.emit("room:create", None, callback=True)


def test_disconnect_pauses_and_reconnect_by_token_restores_state() -> None:
    app, host, guest, created, joined, _ = _two_players()
    _start(host, guest)
    host.get_received()
    guest.disconnect()
    paused = _states(host)[-1]
    assert paused["status"] == "paused"
    assert [p["connected"] for p in paused["players"]] == [True, False]
    assert isinstance(paused["players"][1]["reservationSeconds"], int)

    back = socketio.test_client(app)
    result = back.emit(
        "room:reconnect",
        {"code": created["state"]["code"], "token": joined["token"]},
        callback=True,
    )
    assert result["ok"] is True and result["state"]["you"] == joined["state"]["you"]
    assert (
        len(
            next(p for p in result["state"]["players"] if p["id"] == result["state"]["you"])["hand"]
        )
        == 5
    )
    assert _states(host)[-1]["players"][1]["connected"] is True
    assert "error" in back.emit("room:reconnect", {"code": "ZZZZZZ", "token": "x"}, callback=True)
    # Paused rooms reject plays until the host resumes.
    assert "paused" in host.emit("game:start_turn", {}, callback=True)["error"]
    assert host.emit("room:resume", {}, callback=True) == {"ok": True}
    assert _states(back)[-1]["status"] == "in_progress"


def test_host_removal_and_end() -> None:
    _, host, guest, created, joined, _ = _two_players()
    _start(host, guest)
    assert "error" in guest.emit("room:pause", {}, callback=True)
    assert host.emit("room:pause", {}, callback=True) == {"ok": True}
    assert host.emit("room:resume", {}, callback=True) == {"ok": True}
    assert "error" in host.emit("room:remove", {}, callback=True)
    assert host.emit("room:remove", {"targetId": joined["state"]["you"]}, callback=True) == {
        "ok": True
    }
    final = _states(host)[-1]
    assert final["status"] == "ended" and final["winner"] == created["state"]["you"]
    assert "error" in guest.emit("game:end_turn", {}, callback=True)


def test_host_can_end_room() -> None:
    _, host, guest, *_ = _two_players()
    _start(host, guest)
    assert host.emit("room:end", {}, callback=True) == {"ok": True}
    assert _states(guest)[-1]["status"] == "ended"


def test_pending_action_over_sockets_is_private_to_involved_players() -> None:
    _, host, guest, created, joined, rooms = _two_players()
    _start(host, guest)
    room = next(iter(rooms.rooms.values()))
    assert room.game is not None
    game = room.game
    active_id = game.current_player.id
    mine, theirs = (host, guest) if active_id == created["state"]["you"] else (guest, host)
    mine.emit("game:start_turn", {}, callback=True)
    other = next(p for p in game.players if p.id != active_id)
    card = next(c for c in game.draw_pile if c.startswith("action-debt_collector"))
    game.draw_pile.remove(card)
    game.player(active_id).hand.append(card)
    money = next(c for c in game.draw_pile if c.startswith("money-1-"))
    game.draw_pile.remove(money)
    other.bank.append(money)

    assert mine.emit("game:action", {"cardId": card, "targetId": other.id}, callback=True) == {
        "ok": True
    }
    pending = _states(theirs)[-1]["pending"]
    assert pending["kind"] == "debt_collector" and pending["awaitingId"] == other.id
    assert "error" in mine.emit("game:end_turn", {}, callback=True)
    assert theirs.emit("game:respond", {"response": "bogus"}, callback=True)["error"]
    assert theirs.emit("game:respond", {"response": "accept"}, callback=True) == {"ok": True}
    assert _states(mine)[-1]["pending"]["payment"]["amount"] == 5
    assert theirs.emit("game:pay", {"cardIds": "no"}, callback=True)["error"]
    assert theirs.emit("game:pay", {"cardIds": [money]}, callback=True) == {"ok": True}
    assert _states(mine)[-1]["pending"] is None
