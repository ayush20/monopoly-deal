"""Response windows for cancelable action effects."""

from __future__ import annotations

from dataclasses import dataclass

from .cards import ActionType
from .errors import GameRuleError
from .game import GameState


@dataclass(slots=True)
class JustSayNoWindow:
    """Tracks a single cancelable effect and alternating counter-responses."""

    initiator_id: str
    protected_player_ids: frozenset[str]
    cancelled: bool = False
    last_responder_id: str | None = None

    def play(self, state: GameState, player_id: str, card_id: str) -> bool:
        """Play a valid Just Say No and return whether the original effect survives."""
        if player_id not in self.protected_player_ids and player_id != self.initiator_id:
            raise GameRuleError("Only an affected player or the action initiator may respond.")
        if self.last_responder_id == player_id:
            raise GameRuleError("The same player cannot respond to their own Just Say No.")
        player = state.player(player_id)
        if card_id not in player.hand or state.cards[card_id].action is not ActionType.JUST_SAY_NO:
            raise GameRuleError("A Just Say No card from this player's hand is required.")

        player.hand.remove(card_id)
        state.discard_pile.append(card_id)
        self.cancelled = not self.cancelled
        self.last_responder_id = player_id
        return not self.cancelled

    @property
    def effect_survives(self) -> bool:
        return not self.cancelled
