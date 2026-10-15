from collections import Counter

from app.game.cards import (
    SET_SIZE,
    ActionType,
    CardType,
    Color,
    build_playable_deck,
    deck_type_counts,
)


def test_playable_deck_matches_classic_package_composition() -> None:
    deck = build_playable_deck()

    assert len(deck) == 106
    assert len({card.id for card in deck}) == 106
    assert deck_type_counts(deck) == Counter(
        {
            CardType.MONEY: 20,
            CardType.PROPERTY: 28,
            CardType.PROPERTY_WILD: 11,
            CardType.RENT: 13,
            CardType.ACTION: 34,
        }
    )


def test_property_and_wild_card_composition_is_complete() -> None:
    deck = build_playable_deck()
    properties = [card for card in deck if card.card_type is CardType.PROPERTY]
    wilds = [card for card in deck if card.card_type is CardType.PROPERTY_WILD]

    assert Counter(next(iter(card.colors)) for card in properties) == Counter(
        {
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
    )
    assert len(wilds) == 11
    assert SET_SIZE[Color.RAILROAD] == 4


def test_action_counts_match_the_canonical_deck() -> None:
    actions = [card for card in build_playable_deck() if card.card_type is CardType.ACTION]

    assert Counter(card.action for card in actions) == Counter(
        {
            ActionType.DEAL_BREAKER: 2,
            ActionType.FORCED_DEAL: 3,
            ActionType.SLY_DEAL: 3,
            ActionType.JUST_SAY_NO: 3,
            ActionType.DEBT_COLLECTOR: 3,
            ActionType.BIRTHDAY: 3,
            ActionType.DOUBLE_RENT: 2,
            ActionType.HOUSE: 3,
            ActionType.HOTEL: 2,
            ActionType.PASS_GO: 10,
        }
    )
