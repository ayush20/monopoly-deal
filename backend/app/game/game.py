"""Deterministic setup, turn, and victory transitions for a game."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import StrEnum

from .cards import SET_SIZE, ActionType, Card, CardType, Color, build_playable_deck
from .errors import GameRuleError

HAND_LIMIT = 7
PLAYS_PER_TURN = 3


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
    rng: random.Random = field(default_factory=random.Random)

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
        excess = len(self.current_player.hand) - HAND_LIMIT
        if excess > 0:
            raise GameRuleError(
                f"Discard {excess} card(s) to get down to {HAND_LIMIT} before ending."
            )
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.phase = TurnPhase.AWAITING_TURN_START

    def discard_to_limit(self, player_id: str, card_ids: list[str]) -> None:
        """Discard cards from an over-limit hand; never below the hand limit."""
        player = self._require_active_player(player_id)
        if len(card_ids) != len(set(card_ids)):
            raise GameRuleError("A card can be discarded only once.")
        if len(player.hand) <= HAND_LIMIT:
            raise GameRuleError("Your hand is not over the limit.")
        if any(card_id not in player.hand for card_id in card_ids):
            raise GameRuleError("That card is not in this player's hand.")
        if not card_ids or len(player.hand) - len(card_ids) < HAND_LIMIT:
            raise GameRuleError(f"Discard only enough cards to reach {HAND_LIMIT}.")
        for card_id in card_ids:
            player.hand.remove(card_id)
            self.discard_pile.append(card_id)

    def require_active_player(self, player_id: str) -> PlayerState:
        """Public guard: the player must hold the active turn."""
        return self._require_active_player(player_id)

    def commit_action_cards(self, player_id: str, card_ids: list[str]) -> None:
        """Move hand cards to the discard pile, spending one play per card."""
        player = self._require_active_player(player_id)
        if len(card_ids) != len(set(card_ids)) or any(c not in player.hand for c in card_ids):
            raise GameRuleError("The required cards are not in this player's hand.")
        if self.actions_played + len(card_ids) > PLAYS_PER_TURN:
            raise GameRuleError("A player can play at most three cards each turn.")
        for card_id in card_ids:
            self._use_play()
            player.hand.remove(card_id)
            self.discard_pile.append(card_id)

    def remove_player(self, player_id: str) -> None:
        """Drop a player mid-game, returning their cards to the discard pile."""
        index = next((i for i, p in enumerate(self.players) if p.id == player_id), None)
        if index is None:
            return
        removed = self.players.pop(index)
        self.discard_pile.extend(removed.hand + removed.bank)
        for cards in list(removed.properties.values()) + list(removed.improvements.values()):
            self.discard_pile.extend(cards)
        if not self.players:
            return
        if index < self.current_player_index:
            self.current_player_index -= 1
        elif index == self.current_player_index:
            self.phase = TurnPhase.AWAITING_TURN_START
            self.actions_played = 0
        self.current_player_index %= len(self.players)

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

    def check_sly_deal(
        self, player_id: str, target_id: str, property_card_id: str, color: Color
    ) -> None:
        self._require_other_player(player_id, target_id)
        target_cards = self.player(target_id).properties.get(color, [])
        if property_card_id not in target_cards:
            raise GameRuleError("The target does not own that property in this set.")
        if len(target_cards) >= SET_SIZE[color]:
            raise GameRuleError("A Sly Deal cannot take a property from a complete set.")

    def apply_sly_deal(
        self, player_id: str, target_id: str, property_card_id: str, color: Color
    ) -> None:
        self.check_sly_deal(player_id, target_id, property_card_id, color)
        self.player(target_id).properties[color].remove(property_card_id)
        self.player(player_id).properties.setdefault(color, []).append(property_card_id)
        self.check_for_winner(player_id)

    def play_sly_deal(
        self,
        player_id: str,
        action_card_id: str,
        *,
        target_id: str,
        property_card_id: str,
        color: Color,
    ) -> None:
        """Take one property card that is not in the target's full set."""
        player = self._require_active_player(player_id)
        self._require_hand_action(player, action_card_id, ActionType.SLY_DEAL)
        self.check_sly_deal(player_id, target_id, property_card_id, color)
        self._play_action_card(player, action_card_id)
        self.apply_sly_deal(player_id, target_id, property_card_id, color)

    def check_forced_deal(
        self,
        player_id: str,
        target_id: str,
        offered_property_id: str,
        offered_color: Color,
        requested_property_id: str,
        requested_color: Color,
    ) -> None:
        player = self.player(player_id)
        target = self._require_other_player(player_id, target_id)
        if offered_property_id not in player.properties.get(offered_color, []):
            raise GameRuleError("The offered property is not owned by the active player.")
        target_cards = target.properties.get(requested_color, [])
        if requested_property_id not in target_cards:
            raise GameRuleError("The requested property is not owned by the target.")
        if len(target_cards) >= SET_SIZE[requested_color]:
            raise GameRuleError("A Forced Deal cannot take from a complete set.")

    def apply_forced_deal(
        self,
        player_id: str,
        target_id: str,
        offered_property_id: str,
        offered_color: Color,
        requested_property_id: str,
        requested_color: Color,
    ) -> None:
        self.check_forced_deal(
            player_id,
            target_id,
            offered_property_id,
            offered_color,
            requested_property_id,
            requested_color,
        )
        player, target = self.player(player_id), self.player(target_id)
        player.properties[offered_color].remove(offered_property_id)
        target.properties[requested_color].remove(requested_property_id)
        player.properties.setdefault(requested_color, []).append(requested_property_id)
        target.properties.setdefault(offered_color, []).append(offered_property_id)
        _bank_orphaned_improvements(player, offered_color)
        _bank_orphaned_improvements(target, requested_color)
        self.check_for_winner(player_id)
        self.check_for_winner(target_id)

    def play_forced_deal(
        self,
        player_id: str,
        action_card_id: str,
        *,
        target_id: str,
        offered_property_id: str,
        offered_color: Color,
        requested_property_id: str,
        requested_color: Color,
    ) -> None:
        """Swap one owned property for a target property outside a full set."""
        player = self._require_active_player(player_id)
        self._require_hand_action(player, action_card_id, ActionType.FORCED_DEAL)
        self.check_forced_deal(
            player_id,
            target_id,
            offered_property_id,
            offered_color,
            requested_property_id,
            requested_color,
        )
        self._play_action_card(player, action_card_id)
        self.apply_forced_deal(
            player_id,
            target_id,
            offered_property_id,
            offered_color,
            requested_property_id,
            requested_color,
        )

    def check_deal_breaker(self, player_id: str, target_id: str, color: Color) -> None:
        self._require_other_player(player_id, target_id)
        if len(self.player(target_id).properties.get(color, [])) < SET_SIZE[color]:
            raise GameRuleError("A Deal Breaker requires a complete target set.")

    def apply_deal_breaker(self, player_id: str, target_id: str, color: Color) -> None:
        self.check_deal_breaker(player_id, target_id, color)
        player, target = self.player(player_id), self.player(target_id)
        target_cards = target.properties[color]
        player.properties.setdefault(color, []).extend(target_cards)
        target.properties[color] = []
        player.improvements.setdefault(color, []).extend(target.improvements.pop(color, []))
        self.check_for_winner(player_id)

    def play_deal_breaker(
        self,
        player_id: str,
        action_card_id: str,
        *,
        target_id: str,
        color: Color,
    ) -> None:
        """Take an entire complete set and every attached improvement."""
        player = self._require_active_player(player_id)
        self._require_hand_action(player, action_card_id, ActionType.DEAL_BREAKER)
        self.check_deal_breaker(player_id, target_id, color)
        self._play_action_card(player, action_card_id)
        self.apply_deal_breaker(player_id, target_id, color)

    def _require_other_player(self, player_id: str, target_id: str) -> PlayerState:
        if player_id == target_id:
            raise GameRuleError("An action must target another player.")
        return self.player(target_id)

    def _require_hand_action(
        self,
        player: PlayerState,
        card_id: str,
        action: ActionType,
    ) -> None:
        if card_id not in player.hand or self.cards[card_id].action is not action:
            raise GameRuleError("The required action card is not in this player's hand.")

    def _play_action_card(self, player: PlayerState, card_id: str) -> None:
        self._use_play()
        player.hand.remove(card_id)
        self.discard_pile.append(card_id)

    def _draw_to_hand(self, player: PlayerState, count: int) -> None:
        """Draw up to ``count`` cards, reshuffling the discard pile when the deck runs dry."""
        for _ in range(count):
            if not self.draw_pile:
                if not self.discard_pile:
                    return
                self.draw_pile = self.discard_pile
                self.discard_pile = []
                self.rng.shuffle(self.draw_pile)
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
        if self.actions_played >= PLAYS_PER_TURN:
            raise GameRuleError("A player can play at most three cards each turn.")
        self.actions_played += 1


def _bank_orphaned_improvements(player: PlayerState, color: Color) -> None:
    """Bank improvements when an action breaks their underlying set."""
    if len(player.properties.get(color, [])) < SET_SIZE[color]:
        player.bank.extend(player.improvements.pop(color, []))


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
