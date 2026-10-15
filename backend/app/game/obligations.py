"""Server-owned payment obligations created by card effects."""

from __future__ import annotations

from dataclasses import dataclass, field

from .errors import GameRuleError
from .game import GameState
from .payments import settle_payment


@dataclass(frozen=True, slots=True)
class PaymentObligation:
    payer_id: str
    recipient_id: str
    amount: int
    reason: str


@dataclass(slots=True)
class ObligationQueue:
    """FIFO payment resolution that accepts only the currently liable player."""

    obligations: list[PaymentObligation] = field(default_factory=list)

    @property
    def current(self) -> PaymentObligation | None:
        return self.obligations[0] if self.obligations else None

    @property
    def is_complete(self) -> bool:
        return not self.obligations

    def resolve_current(self, state: GameState, payer_id: str, card_ids: list[str]) -> int:
        obligation = self.current
        if obligation is None:
            raise GameRuleError("There is no payment obligation to resolve.")
        if payer_id != obligation.payer_id:
            raise GameRuleError("Only the current liable player can settle this debt.")
        paid = settle_payment(
            state,
            payer_id=obligation.payer_id,
            recipient_id=obligation.recipient_id,
            amount=obligation.amount,
            card_ids=card_ids,
        )
        self.obligations.pop(0)
        return paid


def birthday_obligations(state: GameState, owner_id: str) -> ObligationQueue:
    """Every other active player owes the owner 2M."""
    return ObligationQueue(
        [
            PaymentObligation(player.id, owner_id, 2, "birthday")
            for player in state.players
            if player.id != owner_id
        ]
    )


def debt_collector_obligation(owner_id: str, target_id: str) -> ObligationQueue:
    """The selected target owes the owner 5M."""
    if owner_id == target_id:
        raise GameRuleError("Debt Collector must target another player.")
    return ObligationQueue([PaymentObligation(target_id, owner_id, 5, "debt_collector")])
