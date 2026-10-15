from typing import cast

from app.rooms import RoomService, RoomStatus


def test_room_starts_with_ready_players_and_hides_opponent_hand() -> None:
    service = RoomService()
    room, host = service.create_room("Ada")
    _, guest = service.join_room(room.code, "Bert")
    service.set_ready(room, host, True)
    service.set_ready(room, guest, True)
    service.start(room, host)

    host_view = service.view(room, host)
    players = {
        cast(str, player["id"]): player
        for player in cast(list[dict[str, object]], host_view["players"])
    }

    assert room.status is RoomStatus.IN_PROGRESS
    assert "hand" in players[host.id]
    assert "hand" not in players[guest.id]


def test_disconnect_pauses_active_game_and_reconnect_restores_member() -> None:
    service = RoomService()
    room, host = service.create_room("Ada", "host-socket")
    _, guest = service.join_room(room.code, "Bert", "guest-socket")
    service.set_ready(room, host, True)
    service.set_ready(room, guest, True)
    service.start(room, host)

    service.disconnect("guest-socket")
    _, restored = service.reconnect(room.code, guest.token, "new-socket")

    assert room.status is RoomStatus.PAUSED
    assert restored.connected is True


def test_host_removal_ends_game_when_one_active_player_remains() -> None:
    service = RoomService()
    room, host = service.create_room("Ada")
    _, guest = service.join_room(room.code, "Bert")
    service.set_ready(room, host, True)
    service.set_ready(room, guest, True)
    service.start(room, host)

    service.host_control(room, host, "remove", guest.id)

    assert room.status is RoomStatus.ENDED
    assert room.game is not None and room.game.winner_id == host.id
