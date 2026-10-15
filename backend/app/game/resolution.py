"""Finalize cancelable actions exactly once after their response window closes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .errors import GameRuleError
from .game import GameState
from .responses import JustSayNoWindow


@dataclass(slots=True)
class PendingResolution:
    """A server-owned action effect waiting for Just Say No responses.

    Socket handlers must create one pending resolution, accept response cards,
    then call :meth:`finalize` exactly once when the response deadline closes.
    """

    window: JustSayNoWindow
    finalized: bool = False

    def respond(self, state: GameState, player_id: str, card_id: str) -> bool:
        if self.finalized:
            raise GameRuleError("This action has already been finalized.")
        return self.window.play(state, player_id, card_id)

    def finalize(self, apply_effect: Callable[[], None]) -> bool:
        """Apply the effect only if it survives; return whether it was applied."""
        if self.finalized:
            raise GameRuleError("This action has already been finalized.")
        self.finalized = True
        if not self.window.effect_survives:
            return False
        apply_effect()
        return True
