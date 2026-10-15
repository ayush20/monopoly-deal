import pytest

from app.game.cards import CardType, Color
from app.game.errors import GameRuleError
from app.game.game import GameState, create_game
from app.game.payments import available_payment_assets, settle_payment


def _move_to_bank(game: GameState, player_id: str, minimum_value: int) -> str:
    player = game.player(player_id)
    card_id = next(
        card_id
        for card_id in game.draw_pile
        if game.cards[card_id].card_type is CardType.MONEY
        and _value_at_least(game, card_id, minimum_value)
    )
    game.draw_pile.remove(card_id)
    player.bank.append(card_id)
    return card_id


def _value_at_least(game: GameState, card_id: str, minimum_value: int) -> bool:
    value = game.cards[card_id].value
    return value is not None and value >= minimum_value


def test_payment_can_overpay_without_change() -> None:
    game = create_game(["ada", "bert"], seed=10)
    card_id = _move_to_bank(game, "ada", 5)

    paid = settle_payment(
        game,
        payer_id="ada",
        recipient_id="bert",
        amount=4,
        card_ids=[card_id],
    )

    assert paid == 5
    assert card_id not in game.player("ada").bank
    assert card_id in game.player("bert").bank


def test_insolvent_player_must_pay_every_available_asset() -> None:
    game = create_game(["ada", "bert"], seed=11)
    first = _move_to_bank(game, "ada", 1)
    second = _move_to_bank(game, "ada", 1)

    with pytest.raises(GameRuleError, match="all available assets"):
        settle_payment(
            game,
            payer_id="ada",
            recipient_id="bert",
            amount=100,
            card_ids=[first],
        )

    paid = settle_payment(
        game,
        payer_id="ada",
        recipient_id="bert",
        amount=100,
        card_ids=[first, second],
    )

    assert paid < 100
    assert game.player("ada").bank == []


def test_laid_property_can_settle_debt_but_hand_cards_cannot() -> None:
    game = create_game(["ada", "bert"], seed=12)
    ada = game.player("ada")
    property_id = next(
        card_id
        for card_id in game.draw_pile
        if game.cards[card_id].card_type is CardType.PROPERTY
        and Color.BROWN in game.cards[card_id].colors
    )
    game.draw_pile.remove(property_id)
    ada.properties[Color.BROWN] = [property_id]

    assets = available_payment_assets(game, "ada")
    assert [asset.card_id for asset in assets] == [property_id]

    settle_payment(
        game,
        payer_id="ada",
        recipient_id="bert",
        amount=1,
        card_ids=[property_id],
    )

    assert property_id in game.player("bert").properties[Color.BROWN]
