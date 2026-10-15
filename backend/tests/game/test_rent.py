import pytest

from app.game.cards import ActionType, Color
from app.game.errors import GameRuleError
from app.game.game import create_game
from app.game.rent import calculate_rent


def test_rent_uses_property_count_and_doubles_when_requested() -> None:
    game = create_game(["ada", "bert"], seed=21)
    game.player("ada").properties[Color.ORANGE] = ["one", "two"]

    assert calculate_rent(game, owner_id="ada", color=Color.ORANGE) == 3
    assert calculate_rent(game, owner_id="ada", color=Color.ORANGE, double_rent=True) == 6


def test_complete_set_applies_house_and_hotel_bonuses() -> None:
    game = create_game(["ada", "bert"], seed=22)
    game.player("ada").properties[Color.BROWN] = ["one", "two"]
    house_id = next(
        card_id for card_id, card in game.cards.items() if card.action is ActionType.HOUSE
    )
    hotel_id = next(
        card_id for card_id, card in game.cards.items() if card.action is ActionType.HOTEL
    )
    game.player("ada").improvements[Color.BROWN] = [house_id, hotel_id]

    assert calculate_rent(game, owner_id="ada", color=Color.BROWN) == 9


def test_rent_rejects_unowned_color() -> None:
    game = create_game(["ada", "bert"], seed=23)

    with pytest.raises(GameRuleError, match="at least one property"):
        calculate_rent(game, owner_id="ada", color=Color.GREEN)
