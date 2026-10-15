import pytest

from app.game.cards import Color
from app.game.errors import GameRuleError
from app.game.game import create_game
from app.game.obligations import birthday_obligations, debt_collector_obligation, rent_obligations


def test_birthday_creates_one_two_million_obligation_per_other_player() -> None:
    game = create_game(["ada", "bert", "cy"], seed=30)

    queue = birthday_obligations(game, "ada")

    assert [(item.payer_id, item.amount) for item in queue.obligations] == [("bert", 2), ("cy", 2)]


def test_only_current_payer_can_resolve_obligation() -> None:
    game = create_game(["ada", "bert"], seed=31)
    queue = debt_collector_obligation("ada", "bert")

    with pytest.raises(GameRuleError, match="current liable"):
        queue.resolve_current(game, "ada", [])


def test_debt_collector_rejects_self_target() -> None:
    with pytest.raises(GameRuleError, match="another player"):
        debt_collector_obligation("ada", "ada")


def test_rent_obligations_use_server_calculated_amount_for_every_target() -> None:
    game = create_game(["ada", "bert", "cy"], seed=32)
    game.player("ada").properties[Color.DARK_BLUE] = ["one", "two"]

    queue = rent_obligations(
        game,
        owner_id="ada",
        color=Color.DARK_BLUE,
        target_ids=["bert", "cy"],
        double_rent=True,
    )

    assert [(item.payer_id, item.amount) for item in queue.obligations] == [
        ("bert", 16),
        ("cy", 16),
    ]


def test_rent_obligations_reject_owner_or_duplicate_targets() -> None:
    game = create_game(["ada", "bert"], seed=33)
    game.player("ada").properties[Color.BROWN] = ["one"]

    with pytest.raises(GameRuleError, match="unique opponents"):
        rent_obligations(
            game,
            owner_id="ada",
            color=Color.BROWN,
            target_ids=["ada", "bert", "bert"],
        )
