"""Deterministic setup, turn, and victory transitions for a game."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import StrEnum

from .cards import SET_SIZE, ActionType, Card, CardType, Color, build_playable_deck
from .errors import GameRuleError


class TurnPhase(StrEnum):
    AWAITING_TURN_START = "awaiting_turn_start"
    ACTIVE = "active"
    COMPLETE = "complete"


@dataclass(slots=True)
class PlayerState:
    """Server-only state for one active player."""

    id: str
    hand: list[str] = field(default_factory=list)
    bank: list[str] = field(default_factory=list)
    properties: dict[Color, list[str]] = field(default_factory=dict)
    improvements: dict[Color, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class GameState:
    """Mutable state owned exclusively by the server transition layer."""

    cards: dict[str, Card]
    players: list[PlayerState]
    draw_pile: list[str]
    discard_pile: list[str] = field(default_factory=list)
    current_player_index: int = 0
    actions_played: int = 0
    phase: TurnPhase = TurnPhase.AWAITING_TURN_START
    winner_id: str | None = None

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def player(self, player_id: str) -> PlayerState:
        for player in self.players:
            if player.id == player_id:
                return player
        raise GameRuleError("Unknown player.")

    def start_turn(self, player_id: str) -> int:
        """Draw the classic two cards, or five when starting with no hand."""
        if self.phase is not TurnPhase.AWAITING_TURN_START:
            raise GameRuleError("A turn is already active.")
        if self.current_player.id != player_id:
            raise GameRuleError("It is not this player's turn.")

        draw_count = 5 if not self.current_player.hand else 2
        self._draw_to_hand(self.current_player, draw_count)
        self.actions_played = 0
        self.phase = TurnPhase.ACTIVE
        return draw_count

    def end_turn(self, player_id: str) -> None:
        if self.phase is not TurnPhase.ACTIVE:
            raise GameRuleError("There is no active turn to end.")
        if self.current_player.id != player_id:
            raise GameRuleError("Only the active player can end their turn.")
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.phase = TurnPhase.AWAITING_TURN_START

    def completed_set_count(self, player_id: str) -> int:
        player = self.player(player_id)
        return sum(1 for color, cards in player.properties.items() if len(cards) >= SET_SIZE[color])

    def check_for_winner(self, player_id: str) -> bool:
        if self.completed_set_count(player_id) < 3:
            return False
        self.winner_id = player_id
        self.phase = TurnPhase.COMPLETE
        return True

    def bank_card(self, player_id: str, card_id: str) -> None:
        """Bank a money, rent, or action card as one of the turn's three plays."""
        player = self._require_active_player(player_id)
        card = self._take_from_hand(player, card_id)
        if card.card_type not in {CardType.MONEY, CardType.RENT, CardType.ACTION}:
            player.hand.append(card_id)
            raise GameRuleError("Only money, rent, and action cards can be banked.")
        self._use_play()
        player.bank.append(card_id)

    def play_property(self, player_id: str, card_id: str, color: Color) -> None:
        """Lay a property or wild property into a compatible property set."""
        player = self._require_active_player(player_id)
        card = self._take_from_hand(player, card_id)
        if card.card_type not in {CardType.PROPERTY, CardType.PROPERTY_WILD}:
            player.hand.append(card_id)
            raise GameRuleError("Only property cards can be played into a property set.")
        if color not in card.colors:
            player.hand.append(card_id)
            raise GameRuleError("That property card cannot be assigned to this color.")
        self._use_play()
        player.properties.setdefault(color, []).append(card_id)
        self.check_for_winner(player_id)

    def move_wild_property(self, player_id: str, card_id: str, destination: Color) -> None:
        """Move an already played wild card during its owner's active turn.

        Reassigning a wild property is a documented turn privilege and does not
        consume one of the three card plays.
        """
        player = self._require_active_player(player_id)
        card = self.cards.get(card_id)
        if card is None or card.card_type is not CardType.PROPERTY_WILD:
            raise GameRuleError("Only a played wild property can be moved.")
        if destination not in card.colors:
            raise GameRuleError("That wild property cannot be assigned to this color.")
        source = next(
            (color for color, cards in player.properties.items() if card_id in cards),
            None,
        )
        if source is None:
            raise GameRuleError("That wild property is not in this player's property area.")
        player.properties[source].remove(card_id)
        player.properties.setdefault(destination, []).append(card_id)
        self.check_for_winner(player_id)

    def play_improvement(self, player_id: str, card_id: str, color: Color) -> None:
        """Play a House or Hotel onto an eligible complete property set."""
        player = self._require_active_player(player_id)
        card = self._take_from_hand(player, card_id)
        if card.action not in {ActionType.HOUSE, ActionType.HOTEL}:
            player.hand.append(card_id)
            raise GameRuleError("Only a House or Hotel card can improve a property set.")
        if len(player.properties.get(color, [])) < SET_SIZE[color]:
            player.hand.append(card_id)
            raise GameRuleError("Only a complete property set can be improved.")
        improvements = player.improvements.setdefault(color, [])
        if card.action is ActionType.HOUSE and improvements:
            player.hand.append(card_id)
            raise GameRuleError("A set can have only one House.")
        if card.action is ActionType.HOTEL and len(improvements) != 1:
            player.hand.append(card_id)
            raise GameRuleError("A Hotel requires exactly one House on the set.")
        self._use_play()
        improvements.append(card_id)

    def play_pass_go(self, player_id: str, card_id: str) -> None:
        """Discard Pass Go, draw two cards, and consume one card play."""
        player = self._require_active_player(player_id)
        card = self._take_from_hand(player, card_id)
        if card.action is not ActionType.PASS_GO:
            player.hand.append(card_id)
            raise GameRuleError("Only a Pass Go card can be used for this action.")
        self._use_play()
        self.discard_pile.append(card_id)
        self._draw_to_hand(player, 2)

    def _draw_to_hand(self, player: PlayerState, count: int) -> None:
        if len(self.draw_pile) < count:
            raise GameRuleError("The draw pile does not contain enough cards.")
        for _ in range(count):
            player.hand.append(self.draw_pile.pop())

    def _require_active_player(self, player_id: str) -> PlayerState:
        if self.phase is not TurnPhase.ACTIVE:
            raise GameRuleError("There is no active turn.")
        if self.current_player.id != player_id:
            raise GameRuleError("It is not this player's turn.")
        return self.current_player

    def _take_from_hand(self, player: PlayerState, card_id: str) -> Card:
        if card_id not in player.hand:
            raise GameRuleError("That card is not in this player's hand.")
        player.hand.remove(card_id)
        return self.cards[card_id]

    def _use_play(self) -> None:
        if self.actions_played >= 3:
            raise GameRuleError("A player can play at most three cards each turn.")
        self.actions_played += 1


def create_game(player_ids: list[str], *, seed: int | None = None) -> GameState:
    """Shuffle and deal five cards to each of two to five distinct players."""
    if not 2 <= len(player_ids) <= 5:
        raise GameRuleError("A game needs between two and five players.")
    if len(set(player_ids)) != len(player_ids):
        raise GameRuleError("Player identifiers must be unique.")

    deck = build_playable_deck()
    random.Random(seed).shuffle(deck)
    state = GameState(
        cards={card.id: card for card in deck},
        players=[PlayerState(id=player_id) for player_id in player_ids],
        draw_pile=[card.id for card in deck],
    )
    for player in state.players:
        state._draw_to_hand(player, 5)
    return state
