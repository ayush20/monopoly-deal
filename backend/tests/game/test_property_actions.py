import pytest

from app.game.cards import ActionType, Color
from app.game.errors import GameRuleError
from app.game.game import GameState, create_game


def _give_action(game: GameState, action: ActionType) -> str:
    card_id = next(card_id for card_id in game.draw_pile if game.cards[card_id].action is action)
    game.draw_pile.remove(card_id)
    game.player("ada").hand.append(card_id)
    return card_id


def test_sly_deal_transfers_property_outside_complete_set() -> None:
    game = create_game(["ada", "bert"], seed=13)
    action_id = _give_action(game, ActionType.SLY_DEAL)
    property_id = next(card_id for card_id in game.draw_pile if "property-brown" in card_id)
    game.draw_pile.remove(property_id)
    game.player("bert").properties[Color.BROWN] = [property_id]
    game.start_turn("ada")

    game.play_sly_deal(
        "ada", action_id, target_id="bert", property_card_id=property_id, color=Color.BROWN
    )

    assert property_id in game.player("ada").properties[Color.BROWN]
    assert action_id in game.discard_pile


def test_sly_deal_rejects_a_card_in_complete_set() -> None:
    game = create_game(["ada", "bert"], seed=14)
    action_id = _give_action(game, ActionType.SLY_DEAL)
    game.player("bert").properties[Color.BROWN] = ["one", "two"]
    game.start_turn("ada")

    with pytest.raises(GameRuleError, match="complete set"):
        game.play_sly_deal(
            "ada", action_id, target_id="bert", property_card_id="one", color=Color.BROWN
        )


def test_forced_deal_swaps_properties_and_deal_breaker_takes_set_with_house() -> None:
    game = create_game(["ada", "bert"], seed=15)
    forced_id = _give_action(game, ActionType.FORCED_DEAL)
    breaker_id = _give_action(game, ActionType.DEAL_BREAKER)
    game.player("ada").properties[Color.RED] = ["ada-red"]
    game.player("bert").properties[Color.YELLOW] = ["bert-yellow"]
    game.start_turn("ada")

    game.play_forced_deal(
        "ada",
        forced_id,
        target_id="bert",
        offered_property_id="ada-red",
        offered_color=Color.RED,
        requested_property_id="bert-yellow",
        requested_color=Color.YELLOW,
    )

    assert "bert-yellow" in game.player("ada").properties[Color.YELLOW]
    assert "ada-red" in game.player("bert").properties[Color.RED]

    game.player("bert").properties[Color.BROWN] = ["brown-one", "brown-two"]
    game.player("bert").improvements[Color.BROWN] = ["house"]
    game.play_deal_breaker("ada", breaker_id, target_id="bert", color=Color.BROWN)

    assert game.player("ada").properties[Color.BROWN] == ["brown-one", "brown-two"]
    assert game.player("ada").improvements[Color.BROWN] == ["house"]
