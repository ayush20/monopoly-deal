"""Room-layer rules: pending actions, Just Say No chains, payments, guards."""

from typing import cast

import pytest

from app.game.cards import ActionType, Color
from app.game.errors import GameRuleError
from app.game.game import GameState, TurnPhase
from app.rooms import Member, Room, RoomError, RoomService, RoomStatus


def _setup() -> tuple[RoomService, Room, Member, Member]:
    service = RoomService()
    room, host = service.create_room("Ada", "s1")
    _, guest = service.join_room(room.code, "Bert", "s2")
    for member in (host, guest):
        service.set_ready(room, member, True)
    service.start(room, host)
    assert room.game is not None
    room.game.current_player_index = [p.id for p in room.game.players].index(host.id)
    service.start_turn(room, host)
    return service, room, host, guest


def _take(game: GameState, prefix: str) -> str:
    """Remove a matching card from the deck, or from any hand if it was dealt."""
    for pile in [game.draw_pile, *(p.hand for p in game.players)]:
        for card_id in pile:
            if card_id.startswith(prefix):
                pile.remove(card_id)
                return card_id
    raise AssertionError(prefix)


def _give(room: Room, member: Member, prefix: str) -> str:
    """Move a card whose id starts with prefix from the deck into the member's hand."""
    game = room.game
    assert game is not None
    card_id = _take(game, prefix)
    game.player(member.id).hand.append(card_id)
    return card_id


def _own(room: Room, member: Member, prefix: str, color: Color) -> str:
    game = room.game
    assert game is not None
    card_id = _take(game, prefix)
    game.player(member.id).properties.setdefault(color, []).append(card_id)
    return card_id


def _bank(room: Room, member: Member, prefix: str) -> str:
    game = room.game
    assert game is not None
    card_id = _take(game, prefix)
    game.player(member.id).bank.append(card_id)
    return card_id


def test_sly_deal_accepted_moves_property_and_clears_pending() -> None:
    service, room, host, guest = _setup()
    sly = _give(room, host, "action-sly_deal")
    prop = _own(room, guest, "property-brown", Color.BROWN)

    service.action(room, host, sly, {"targetId": guest.id, "propertyId": prop, "color": "brown"})
    assert room.pending is not None and room.pending.awaiting_id == guest.id
    assert room.game is not None and room.game.actions_played == 1
    with pytest.raises(RoomError, match="pending"):
        service.end_turn(room, host)

    service.respond(room, guest, True)

    assert room.pending is None
    assert prop in room.game.player(host.id).properties[Color.BROWN]
    assert sly in room.game.discard_pile


def test_just_say_no_chain_cancels_then_counter_restores() -> None:
    service, room, host, guest = _setup()
    sly = _give(room, host, "action-sly_deal")
    prop = _own(room, guest, "property-brown", Color.BROWN)
    guest_jsn = _give(room, guest, "action-just_say_no")
    host_jsn = _give(room, host, "action-just_say_no")
    service.action(room, host, sly, {"targetId": guest.id, "propertyId": prop, "color": "brown"})

    service.respond(room, guest, False, guest_jsn)
    assert room.pending is not None and room.pending.awaiting_id == host.id
    with pytest.raises(GameRuleError, match="not your turn"):
        service.respond(room, guest, True)
    service.respond(room, host, False, host_jsn)
    assert room.pending.awaiting_id == guest.id
    service.respond(room, guest, True)  # guest gives up: the Sly Deal survives

    assert room.pending is None
    assert prop in room.game.player(host.id).properties[Color.BROWN]


def test_just_say_no_cancels_effect() -> None:
    service, room, host, guest = _setup()
    sly = _give(room, host, "action-sly_deal")
    prop = _own(room, guest, "property-brown", Color.BROWN)
    jsn = _give(room, guest, "action-just_say_no")
    service.action(room, host, sly, {"targetId": guest.id, "propertyId": prop, "color": "brown"})

    service.respond(room, guest, False, jsn)
    service.respond(room, host, True)

    assert room.pending is None and room.game is not None
    assert prop in room.game.player(guest.id).properties[Color.BROWN]
    assert jsn in room.game.discard_pile


def test_debt_collector_payment_flow() -> None:
    service, room, host, guest = _setup()
    card = _give(room, host, "action-debt_collector")
    _bank(room, guest, "money-10")
    five = _bank(room, guest, "money-5")
    service.action(room, host, card, {"targetId": guest.id})
    service.respond(room, guest, True)

    assert room.pending is not None and room.pending.stage.value == "payment"
    view = cast(dict[str, object], service.view(room, guest)["pending"])
    assert cast(dict[str, object], view["payment"])["amount"] == 5
    assert service.view(room, host)["pending"] is not None
    with pytest.raises(GameRuleError, match="not your turn"):
        service.pay(room, host, [])

    service.pay(room, guest, [five])

    assert room.pending is None and room.game is not None
    assert five in room.game.player(host.id).bank


def test_birthday_skips_players_with_nothing_and_blocks_underpay() -> None:
    service = RoomService()
    room, host = service.create_room("Ada", "s1")
    members = [host]
    for index in range(2):
        members.append(service.join_room(room.code, f"P{index}", f"s{index + 2}")[1])
    for member in members:
        service.set_ready(room, member, True)
    service.start(room, host)
    assert room.game is not None
    room.game.current_player_index = 0
    service.start_turn(room, host)
    _, rich, poor = members
    card = _give(room, host, "action-birthday")
    ones = [_bank(room, rich, "money-1-") for _ in range(1)]
    service.action(room, host, card, {})
    service.respond(room, rich, True)
    service.respond(room, poor, True)
    # poor has nothing so was auto-settled; rich owes 2 with only 1 laid: must pay all
    assert room.pending is not None and room.pending.awaiting_id == rich.id
    with pytest.raises(GameRuleError, match="pay all"):
        service.pay(room, rich, [])
    service.pay(room, rich, ones)
    assert room.pending is None


def test_double_rent_costs_two_plays_and_doubles_amount() -> None:
    service, room, host, guest = _setup()
    rent = _give(room, host, "rent-any")
    double = _give(room, host, "action-double_rent")
    _own(room, host, "property-brown", Color.BROWN)
    _bank(room, guest, "money-10")
    service.action(
        room,
        host,
        rent,
        {"color": "brown", "targetId": guest.id, "doubleRentCardId": double},
    )
    assert room.game is not None and room.game.actions_played == 2
    service.respond(room, guest, True)
    assert room.pending is not None and room.pending.payments is not None
    assert room.pending.payments.obligations[0].amount == 2


def test_action_validation_errors_do_not_spend_plays() -> None:
    service, room, host, guest = _setup()
    sly = _give(room, host, "action-sly_deal")
    assert room.game is not None
    with pytest.raises(GameRuleError, match="does not own"):
        service.action(room, host, sly, {"targetId": guest.id, "propertyId": "x", "color": "pink"})
    with pytest.raises(GameRuleError, match="cannot be played"):
        service.action(room, host, _give(room, host, "action-house"), {})
    assert room.game.actions_played == 0 and room.pending is None
    assert sly in room.game.player(host.id).hand


def test_winning_play_ends_room_and_blocks_further_commands() -> None:
    service, room, host, guest = _setup()
    for color in (Color.BROWN, Color.DARK_BLUE):
        for _ in range(2):
            _own(room, host, f"property-{color.value}", color)
    _own(room, host, "property-utility", Color.UTILITY)
    last = _give(room, host, "property-utility")

    service.play_property(room, host, last, Color.UTILITY)

    assert room.status is RoomStatus.ENDED and room.game is not None
    assert room.game.winner_id == host.id
    assert room.game.phase is TurnPhase.COMPLETE
    with pytest.raises(RoomError, match="over"):
        service.end_turn(room, host)


def test_commands_blocked_when_paused_or_not_your_turn() -> None:
    service, room, host, guest = _setup()
    with pytest.raises(GameRuleError, match="not this player's turn"):
        service.bank(room, guest, "x")
    service.host_control(room, host, "pause")
    with pytest.raises(RoomError, match="paused"):
        service.end_turn(room, host)


def test_card_catalog_and_view_fields() -> None:
    service, room, host, guest = _setup()
    view = service.view(room, host)
    assert view["you"] == host.id
    assert len(cast(dict[str, object], view["cards"])) == 106
    turn = cast(dict[str, object], view["turn"])
    assert turn["playsMax"] == 3 and turn["phase"] == "active"
    assert view["drawCount"] == 106 - 10 - 2 and view["winner"] is None
    sly = cast(dict[str, dict[str, object]], view["cards"])["action-sly_deal-1"]
    assert sly["name"] == "Sly Deal" and sly["action"] == ActionType.SLY_DEAL.value
    assert service.view(room, guest)["pending"] is None


def test_removing_player_clears_their_pending_action() -> None:
    service = RoomService()
    room, host = service.create_room("Ada", "s1")
    others = [service.join_room(room.code, n, f"s-{n}")[1] for n in ("B", "C")]
    for member in [host, *others]:
        service.set_ready(room, member, True)
    service.start(room, host)
    assert room.game is not None
    room.game.current_player_index = 0
    service.start_turn(room, host)
    card = _give(room, host, "action-birthday")
    service.action(room, host, card, {})
    service.host_control(room, host, "remove", others[0].id)
    assert room.pending is None and room.status is RoomStatus.IN_PROGRESS
