import pytest

from app.game.cards import ActionType
from app.game.errors import GameRuleError
from app.game.game import GameState, create_game
from app.game.responses import JustSayNoWindow


def _give_just_say_no(game: GameState, player_id: str) -> str:
    card_id = next(
        card_id
        for card_id in game.draw_pile
        if game.cards[card_id].action is ActionType.JUST_SAY_NO
    )
    game.draw_pile.remove(card_id)
    game.player(player_id).hand.append(card_id)
    return card_id


def test_just_say_no_cancels_then_initiator_can_counter_cancel() -> None:
    game = create_game(["ada", "bert"], seed=40)
    bert_card = _give_just_say_no(game, "bert")
    ada_card = _give_just_say_no(game, "ada")
    window = JustSayNoWindow("ada", frozenset({"bert"}))

    assert window.play(game, "bert", bert_card) is False
    assert window.cancelled is True
    assert window.play(game, "ada", ada_card) is True
    assert window.effect_survives is True


def test_unaffected_player_cannot_use_just_say_no() -> None:
    game = create_game(["ada", "bert", "cy"], seed=41)
    cy_card = _give_just_say_no(game, "cy")
    window = JustSayNoWindow("ada", frozenset({"bert"}))

    with pytest.raises(GameRuleError, match="affected player"):
        window.play(game, "cy", cy_card)
