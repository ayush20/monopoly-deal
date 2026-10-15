"""Authoritative rent calculation from server-owned property state."""

from __future__ import annotations

from .cards import RENT_SCHEDULE, SET_SIZE, ActionType, Color
from .errors import GameRuleError
from .game import GameState


def calculate_rent(
    state: GameState,
    *,
    owner_id: str,
    color: Color,
    double_rent: bool = False,
) -> int:
    """Return the owed amount for a colour currently owned by a player.

    House and Hotel bonuses apply only to full sets. The caller must separately
    validate that a played rent card permits the chosen colour.
    """
    owner = state.player(owner_id)
    property_count = len(owner.properties.get(color, []))
    if property_count == 0:
        raise GameRuleError("Rent requires at least one property in the chosen color.")

    capped_count = min(property_count, SET_SIZE[color])
    rent = RENT_SCHEDULE[color][capped_count - 1]
    if property_count >= SET_SIZE[color]:
        improvements = owner.improvements.get(color, [])
        rent += 3 * sum(state.cards[card_id].action is ActionType.HOUSE for card_id in improvements)
        rent += 4 * sum(state.cards[card_id].action is ActionType.HOTEL for card_id in improvements)
    return rent * 2 if double_rent else rent
