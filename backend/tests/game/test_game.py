import pytest

from app.game.cards import ActionType, CardType, Color
from app.game.errors import GameRuleError
from app.game.game import TurnPhase, create_game


def test_game_deals_five_cards_and_seeded_shuffle_is_reproducible() -> None:
    first = create_game(["ada", "bert", "cy"], seed=9)
    second = create_game(["ada", "bert", "cy"], seed=9)

    assert [player.hand for player in first.players] == [player.hand for player in second.players]
    assert all(len(player.hand) == 5 for player in first.players)
    assert len(first.draw_pile) == 91
    assert first.phase is TurnPhase.AWAITING_TURN_START


def test_turn_draws_two_when_player_has_cards_then_advances() -> None:
    game = create_game(["ada", "bert"], seed=1)

    assert game.start_turn("ada") == 2
    assert len(game.player("ada").hand) == 7
    assert game.actions_played == 0
    assert game.phase is TurnPhase.ACTIVE

    game.end_turn("ada")

    assert game.current_player.id == "bert"
    assert game.phase is TurnPhase.AWAITING_TURN_START


def test_empty_hand_draws_five_at_turn_start() -> None:
    game = create_game(["ada", "bert"], seed=2)
    game.player("ada").hand.clear()

    assert game.start_turn("ada") == 5
    assert len(game.player("ada").hand) == 5


def test_turn_transitions_reject_out_of_turn_or_duplicate_requests() -> None:
    game = create_game(["ada", "bert"], seed=3)

    with pytest.raises(GameRuleError, match="not this player's turn"):
        game.start_turn("bert")

    game.start_turn("ada")
    with pytest.raises(GameRuleError, match="already active"):
        game.start_turn("ada")
    with pytest.raises(GameRuleError, match="active player"):
        game.end_turn("bert")


def test_three_complete_sets_end_the_game() -> None:
    game = create_game(["ada", "bert"], seed=4)
    ada = game.player("ada")
    ada.properties = {
        Color.BROWN: ["a", "b"],
        Color.LIGHT_BLUE: ["c", "d", "e"],
        Color.DARK_BLUE: ["f", "g"],
    }

    assert game.check_for_winner("ada") is True
    assert game.winner_id == "ada"
    assert game.phase is TurnPhase.COMPLETE


def test_bank_and_property_plays_are_limited_to_three_cards() -> None:
    game = create_game(["ada", "bert"], seed=5)
    game.start_turn("ada")
    ada = game.player("ada")
    bankable_cards = [
        card_id
        for card_id in ada.hand
        if game.cards[card_id].card_type in {CardType.MONEY, CardType.RENT, CardType.ACTION}
    ]
    while len(bankable_cards) < 4:
        next_card = next(
            card_id for card_id in game.draw_pile if game.cards[card_id].value is not None
        )
        game.draw_pile.remove(next_card)
        ada.hand.append(next_card)
        bankable_cards.append(next_card)

    for card_id in bankable_cards[:3]:
        game.bank_card("ada", card_id)

    with pytest.raises(GameRuleError, match="at most three"):
        game.bank_card("ada", bankable_cards[3])


def test_wild_property_must_use_a_supported_color_and_can_be_reassigned() -> None:
    game = create_game(["ada", "bert"], seed=6)
    game.start_turn("ada")
    ada = game.player("ada")
    wild_id = next(
        card_id
        for card_id in game.draw_pile
        if game.cards[card_id].card_type is CardType.PROPERTY_WILD
        and Color.RED in game.cards[card_id].colors
    )
    game.draw_pile.remove(wild_id)
    ada.hand.append(wild_id)

    game.play_property("ada", wild_id, Color.RED)
    game.move_wild_property("ada", wild_id, Color.YELLOW)

    assert wild_id not in ada.properties[Color.RED]
    assert wild_id in ada.properties[Color.YELLOW]


def test_house_and_hotel_require_a_complete_set_in_order() -> None:
    game = create_game(["ada", "bert"], seed=7)
    game.start_turn("ada")
    ada = game.player("ada")
    ada.properties[Color.BROWN] = ["brown-a", "brown-b"]
    house_id = next(
        card_id for card_id in game.draw_pile if game.cards[card_id].action is ActionType.HOUSE
    )
    hotel_id = next(
        card_id for card_id in game.draw_pile if game.cards[card_id].action is ActionType.HOTEL
    )
    game.draw_pile.remove(house_id)
    game.draw_pile.remove(hotel_id)
    ada.hand.extend([house_id, hotel_id])

    game.play_improvement("ada", house_id, Color.BROWN)
    game.play_improvement("ada", hotel_id, Color.BROWN)

    assert ada.improvements[Color.BROWN] == [house_id, hotel_id]
