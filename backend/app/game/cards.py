"""Canonical playable-card data for the 110-card classic package.

The package includes four reference cards. They are intentionally excluded from
the 106-card playable deck returned by :func:`build_playable_deck`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum


class Color(StrEnum):
    BROWN = "brown"
    LIGHT_BLUE = "light_blue"
    PINK = "pink"
    ORANGE = "orange"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    DARK_BLUE = "dark_blue"
    RAILROAD = "railroad"
    UTILITY = "utility"


class CardType(StrEnum):
    MONEY = "money"
    PROPERTY = "property"
    PROPERTY_WILD = "property_wild"
    RENT = "rent"
    ACTION = "action"


class ActionType(StrEnum):
    DEAL_BREAKER = "deal_breaker"
    FORCED_DEAL = "forced_deal"
    SLY_DEAL = "sly_deal"
    JUST_SAY_NO = "just_say_no"
    DEBT_COLLECTOR = "debt_collector"
    BIRTHDAY = "birthday"
    DOUBLE_RENT = "double_rent"
    HOUSE = "house"
    HOTEL = "hotel"
    PASS_GO = "pass_go"


SET_SIZE: dict[Color, int] = {
    Color.BROWN: 2,
    Color.LIGHT_BLUE: 3,
    Color.PINK: 3,
    Color.ORANGE: 3,
    Color.RED: 3,
    Color.YELLOW: 3,
    Color.GREEN: 3,
    Color.DARK_BLUE: 2,
    Color.RAILROAD: 4,
    Color.UTILITY: 2,
}

RENT_SCHEDULE: dict[Color, tuple[int, ...]] = {
    Color.BROWN: (1, 2),
    Color.LIGHT_BLUE: (1, 2, 3),
    Color.PINK: (1, 2, 4),
    Color.ORANGE: (1, 3, 5),
    Color.RED: (2, 3, 6),
    Color.YELLOW: (2, 4, 6),
    Color.GREEN: (2, 4, 7),
    Color.DARK_BLUE: (3, 8),
    Color.RAILROAD: (1, 2, 3, 4),
    Color.UTILITY: (1, 2),
}


@dataclass(frozen=True, slots=True)
class Card:
    """One physical playable card with a stable server-side identifier."""

    id: str
    card_type: CardType
    value: int | None
    colors: frozenset[Color] = frozenset()
    action: ActionType | None = None


def _copies(
    cards: list[Card],
    *,
    prefix: str,
    count: int,
    card_type: CardType,
    value: int | None,
    colors: frozenset[Color] = frozenset(),
    action: ActionType | None = None,
) -> None:
    for number in range(1, count + 1):
        cards.append(
            Card(
                id=f"{prefix}-{number}",
                card_type=card_type,
                value=value,
                colors=colors,
                action=action,
            )
        )


def build_playable_deck() -> list[Card]:
    """Build the 106 playable cards from the classic 110-card package."""
    cards: list[Card] = []

    for color, count in {
        Color.BROWN: 2,
        Color.LIGHT_BLUE: 3,
        Color.PINK: 3,
        Color.ORANGE: 3,
        Color.RED: 3,
        Color.YELLOW: 3,
        Color.GREEN: 3,
        Color.DARK_BLUE: 2,
        Color.RAILROAD: 4,
        Color.UTILITY: 2,
    }.items():
        _copies(
            cards,
            prefix=f"property-{color.value}",
            count=count,
            card_type=CardType.PROPERTY,
            value=None,
            colors=frozenset({color}),
        )

    for first, second, count in (
        (Color.LIGHT_BLUE, Color.BROWN, 1),
        (Color.LIGHT_BLUE, Color.RAILROAD, 1),
        (Color.PINK, Color.ORANGE, 2),
        (Color.RED, Color.YELLOW, 2),
        (Color.DARK_BLUE, Color.GREEN, 1),
        (Color.GREEN, Color.RAILROAD, 1),
        (Color.RAILROAD, Color.UTILITY, 1),
    ):
        _copies(
            cards,
            prefix=f"wild-{first.value}-{second.value}",
            count=count,
            card_type=CardType.PROPERTY_WILD,
            value=None,
            colors=frozenset({first, second}),
        )
    _copies(
        cards,
        prefix="wild-any",
        count=2,
        card_type=CardType.PROPERTY_WILD,
        value=None,
        colors=frozenset(Color),
    )

    for first, second, count in (
        (Color.LIGHT_BLUE, Color.BROWN, 2),
        (Color.PINK, Color.ORANGE, 2),
        (Color.RED, Color.YELLOW, 2),
        (Color.DARK_BLUE, Color.GREEN, 2),
        (Color.RAILROAD, Color.UTILITY, 2),
    ):
        _copies(
            cards,
            prefix=f"rent-{first.value}-{second.value}",
            count=count,
            card_type=CardType.RENT,
            value=1,
            colors=frozenset({first, second}),
        )
    _copies(
        cards,
        prefix="rent-any",
        count=3,
        card_type=CardType.RENT,
        value=3,
        colors=frozenset(Color),
    )

    for action, count, value in (
        (ActionType.DEAL_BREAKER, 2, 5),
        (ActionType.FORCED_DEAL, 3, 3),
        (ActionType.SLY_DEAL, 3, 3),
        (ActionType.JUST_SAY_NO, 3, 4),
        (ActionType.DEBT_COLLECTOR, 3, 3),
        (ActionType.BIRTHDAY, 3, 2),
        (ActionType.DOUBLE_RENT, 2, 1),
        (ActionType.HOUSE, 3, 3),
        (ActionType.HOTEL, 2, 4),
        (ActionType.PASS_GO, 10, 1),
    ):
        _copies(
            cards,
            prefix=f"action-{action.value}",
            count=count,
            card_type=CardType.ACTION,
            value=value,
            action=action,
        )

    for value, count in ((1, 6), (2, 5), (3, 3), (4, 3), (5, 2), (10, 1)):
        _copies(
            cards,
            prefix=f"money-{value}",
            count=count,
            card_type=CardType.MONEY,
            value=value,
        )

    return cards


def deck_type_counts(deck: list[Card]) -> Counter[CardType]:
    """Return physical-card counts by type for integrity assertions."""
    return Counter(card.card_type for card in deck)
