import pytest

from app.game.cards import Color
from app.game.errors import GameRuleError
from app.game.game import GameState, create_game


def _started() -> GameState:
    game = create_game(["ada", "bert"], seed=7)
    game.start_turn("ada")
    return game


def test_end_turn_rejected_while_hand_over_limit() -> None:
    game = _started()
    game.player("ada").hand.extend(game.draw_pile[:2])  # 7 + 2 = 9 cards
    del game.draw_pile[:2]

    with pytest.raises(GameRuleError, match="Discard 2"):
        game.end_turn("ada")


def test_discard_to_limit_then_end_turn() -> None:
    game = _started()
    ada = game.player("ada")
    ada.hand.extend(game.draw_pile[:2])
    del game.draw_pile[:2]
    discards = ada.hand[:2]

    game.discard_to_limit("ada", discards)
    game.end_turn("ada")

    assert len(ada.hand) == 7
    assert game.discard_pile[-2:] == discards


def test_discard_to_limit_rejects_bad_requests() -> None:
    game = _started()
    ada = game.player("ada")
    with pytest.raises(GameRuleError, match="not over"):
        game.discard_to_limit("ada", [ada.hand[0]])
    ada.hand.extend(game.draw_pile[:1])
    del game.draw_pile[:1]
    with pytest.raises(GameRuleError, match="only enough"):
        game.discard_to_limit("ada", ada.hand[:3])
    with pytest.raises(GameRuleError, match="not in this player's hand"):
        game.discard_to_limit("ada", ["nope"])
    with pytest.raises(GameRuleError, match="only once"):
        game.discard_to_limit("ada", [ada.hand[0], ada.hand[0]])


def test_draw_reshuffles_discard_pile_when_deck_runs_out() -> None:
    game = create_game(["ada", "bert"], seed=3)
    game.discard_pile = game.draw_pile[:20]
    game.draw_pile = game.draw_pile[20:21]  # one card left
    ada = game.player("ada")

    game.start_turn("ada")

    assert len(ada.hand) == 5 + 2
    assert len(game.draw_pile) == 19
    assert game.discard_pile == []
    all_cards = game.draw_pile + [c for p in game.players for c in p.hand] + game.discard_pile
    assert len(set(all_cards)) == len(all_cards)


def test_draw_stops_quietly_when_no_cards_anywhere() -> None:
    game = create_game(["ada", "bert"], seed=3)
    game.draw_pile = []
    game.discard_pile = []
    game.start_turn("ada")
    assert len(game.player("ada").hand) == 5


def test_plays_rejected_after_a_winner() -> None:
    game = _started()
    ada = game.player("ada")
    ada.properties = {c: ["x"] * 9 for c in list(Color)[:3]}
    assert game.check_for_winner("ada")
    with pytest.raises(GameRuleError):
        game.bank_card("ada", ada.hand[0])
    with pytest.raises(GameRuleError):
        game.end_turn("ada")
