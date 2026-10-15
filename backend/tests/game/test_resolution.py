import pytest

from app.game.errors import GameRuleError
from app.game.resolution import PendingResolution
from app.game.responses import JustSayNoWindow


def test_cancelled_pending_effect_is_not_applied() -> None:
    resolution = PendingResolution(JustSayNoWindow("ada", frozenset({"bert"}), cancelled=True))
    calls: list[str] = []

    assert resolution.finalize(lambda: calls.append("applied")) is False
    assert calls == []


def test_effect_applies_once_and_cannot_finalize_twice() -> None:
    resolution = PendingResolution(JustSayNoWindow("ada", frozenset({"bert"})))
    calls: list[str] = []

    assert resolution.finalize(lambda: calls.append("applied")) is True
    with pytest.raises(GameRuleError, match="already"):
        resolution.finalize(lambda: calls.append("again"))
    assert calls == ["applied"]
