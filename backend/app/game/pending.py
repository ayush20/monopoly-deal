"""Server-held pending actions: Just Say No responses followed by payments.

Flow: the active player commits an action card (spending plays). Each affected
player, one at a time, either accepts or plays Just Say No; the initiator may
counter, and so on. There is no timer. Surviving payment effects then enter an
``ObligationQueue`` that the liable players settle in order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .cards import ActionType, CardType, Color
from .errors import GameRuleError
from .game import GameState
from .obligations import (
    ObligationQueue,
    PaymentObligation,
    birthday_obligations,
    debt_collector_obligation,
    rent_obligations,
)
from .payments import available_payment_assets
from .resolution import PendingResolution
from .responses import JustSayNoWindow

RENT_KIND = "rent"
PAYMENT_KINDS = {ActionType.BIRTHDAY.value, ActionType.DEBT_COLLECTOR.value, RENT_KIND}
PLAYABLE_ACTIONS = {
    ActionType.SLY_DEAL,
    ActionType.FORCED_DEAL,
    ActionType.DEAL_BREAKER,
    ActionType.DEBT_COLLECTOR,
    ActionType.BIRTHDAY,
}


class Stage(StrEnum):
    RESPONSE = "response"
    PAYMENT = "payment"


@dataclass(slots=True)
class PendingAction:
    kind: str
    initiator_id: str
    card_ids: list[str]
    targets: list[str]
    params: dict[str, str]
    awaiting_id: str
    obligations: ObligationQueue | None = None
    stage: Stage = Stage.RESPONSE
    target_index: int = 0
    survivors: list[str] = field(default_factory=list)
    resolution: PendingResolution | None = None
    payments: ObligationQueue | None = None

    @property
    def current_target(self) -> str | None:
        if self.stage is Stage.RESPONSE and self.target_index < len(self.targets):
            return self.targets[self.target_index]
        return None

    def involves(self, player_id: str) -> bool:
        return player_id == self.initiator_id or player_id in self.targets

    def involves_any(self, player_ids: set[str]) -> bool:
        return any(self.involves(player_id) for player_id in player_ids)


def _text(params: dict[str, str], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise GameRuleError(f"Missing required field: {key}.")
    return value


def _color(params: dict[str, str], key: str) -> Color:
    try:
        return Color(_text(params, key))
    except ValueError:
        raise GameRuleError(f"Unknown color for {key}.") from None


def _open_window(pending: PendingAction) -> None:
    target = pending.targets[pending.target_index]
    pending.awaiting_id = target
    pending.resolution = PendingResolution(
        JustSayNoWindow(pending.initiator_id, frozenset({target}))
    )


def create_pending(
    game: GameState, player_id: str, card_id: str, params: dict[str, str]
) -> PendingAction:
    """Validate an action card play, commit its cards, and open the first response."""
    game.require_active_player(player_id)
    player = game.player(player_id)
    if card_id not in player.hand:
        raise GameRuleError("That card is not in this player's hand.")
    card = game.cards[card_id]
    card_ids = [card_id]
    obligations: ObligationQueue | None = None
    others = [p.id for p in game.players if p.id != player_id]
    targets: list[str]
    clean: dict[str, str] = {}

    if card.card_type is CardType.RENT:
        kind = RENT_KIND
        color = _color(params, "color")
        if color not in card.colors:
            raise GameRuleError("That rent card cannot charge this color.")
        double = params.get("doubleRentCardId")
        if double:
            if double not in player.hand or game.cards[double].action is not ActionType.DOUBLE_RENT:
                raise GameRuleError("The Double Rent card is not in this player's hand.")
            card_ids.append(double)
        if len(card.colors) > 2:
            target = _text(params, "targetId")
            if target not in others:
                raise GameRuleError("Rent must target another player.")
            targets = [target]
            clean["targetId"] = target
        else:
            targets = others
        obligations = rent_obligations(
            game, owner_id=player_id, color=color, target_ids=targets, double_rent=bool(double)
        )
        clean["color"] = color.value
        if double:
            clean["doubleRentCardId"] = double
    elif card.card_type is CardType.ACTION and card.action in PLAYABLE_ACTIONS:
        assert card.action is not None
        kind = card.action.value
        if card.action is ActionType.BIRTHDAY:
            targets = others
            obligations = birthday_obligations(game, player_id)
        else:
            target = _text(params, "targetId")
            game.player(target)
            clean["targetId"] = target
            targets = [target]
            if card.action is ActionType.DEBT_COLLECTOR:
                obligations = debt_collector_obligation(player_id, target)
            elif card.action is ActionType.SLY_DEAL:
                prop, color = _text(params, "propertyId"), _color(params, "color")
                game.check_sly_deal(player_id, target, prop, color)
                clean.update(propertyId=prop, color=color.value)
            elif card.action is ActionType.FORCED_DEAL:
                offered = _text(params, "offeredId")
                offered_color = _color(params, "offeredColor")
                wanted = _text(params, "requestedId")
                wanted_color = _color(params, "requestedColor")
                game.check_forced_deal(
                    player_id, target, offered, offered_color, wanted, wanted_color
                )
                clean.update(
                    offeredId=offered,
                    offeredColor=offered_color.value,
                    requestedId=wanted,
                    requestedColor=wanted_color.value,
                )
            else:
                color = _color(params, "color")
                game.check_deal_breaker(player_id, target, color)
                clean["color"] = color.value
    else:
        raise GameRuleError("That card cannot be played as an action.")

    if not targets:
        raise GameRuleError("There is no one to target.")
    game.commit_action_cards(player_id, card_ids)
    pending = PendingAction(
        kind=kind,
        initiator_id=player_id,
        card_ids=card_ids,
        targets=targets,
        params=clean,
        awaiting_id=targets[0],
        obligations=obligations,
    )
    _open_window(pending)
    return pending


def play_just_say_no(game: GameState, pending: PendingAction, player_id: str, card_id: str) -> None:
    """Counter the current effect; the other party is asked next."""
    _require_awaiting(pending, player_id, Stage.RESPONSE)
    assert pending.resolution is not None
    pending.resolution.respond(game, player_id, card_id)
    target = pending.targets[pending.target_index]
    pending.awaiting_id = pending.initiator_id if player_id == target else target


def accept(game: GameState, pending: PendingAction, player_id: str) -> bool:
    """Accept the current state of the exchange. Returns True when fully resolved."""
    _require_awaiting(pending, player_id, Stage.RESPONSE)
    assert pending.resolution is not None
    target = pending.targets[pending.target_index]
    pending.resolution.finalize(lambda: _effect_survived(game, pending, target))
    pending.target_index += 1
    if pending.target_index < len(pending.targets):
        _open_window(pending)
        return False
    return _begin_payments(game, pending)


def pay(game: GameState, pending: PendingAction, player_id: str, card_ids: list[str]) -> bool:
    """Settle the current debt. Returns True when the pending action is finished."""
    _require_awaiting(pending, player_id, Stage.PAYMENT)
    assert pending.payments is not None
    pending.payments.resolve_current(game, player_id, card_ids)
    game.check_for_winner(pending.initiator_id)
    return _advance_payments(game, pending)


def _effect_survived(game: GameState, pending: PendingAction, target: str) -> None:
    params, who = pending.params, pending.initiator_id
    if pending.kind in PAYMENT_KINDS:
        pending.survivors.append(target)
    elif pending.kind == ActionType.SLY_DEAL.value:
        game.apply_sly_deal(who, target, params["propertyId"], Color(params["color"]))
    elif pending.kind == ActionType.FORCED_DEAL.value:
        game.apply_forced_deal(
            who,
            target,
            params["offeredId"],
            Color(params["offeredColor"]),
            params["requestedId"],
            Color(params["requestedColor"]),
        )
    elif pending.kind == ActionType.DEAL_BREAKER.value:
        game.apply_deal_breaker(who, target, Color(params["color"]))


def _begin_payments(game: GameState, pending: PendingAction) -> bool:
    if pending.kind not in PAYMENT_KINDS or pending.obligations is None:
        return True
    surviving = [o for o in pending.obligations.obligations if o.payer_id in pending.survivors]
    if not surviving:
        return True
    pending.stage = Stage.PAYMENT
    pending.payments = ObligationQueue(list(surviving))
    return _advance_payments(game, pending)


def _advance_payments(game: GameState, pending: PendingAction) -> bool:
    queue = pending.payments
    assert queue is not None
    while (current := queue.current) is not None:
        if game.winner_id is not None:
            return True
        if available_payment_assets(game, current.payer_id):
            pending.awaiting_id = current.payer_id
            return False
        # Nothing laid down to pay with: the debt resolves for nothing.
        queue.resolve_current(game, current.payer_id, [])
    return True


def current_obligation(pending: PendingAction) -> PaymentObligation | None:
    return pending.payments.current if pending.payments else None


def _require_awaiting(pending: PendingAction, player_id: str, stage: Stage) -> None:
    if pending.stage is not stage:
        raise GameRuleError("That response is not expected right now.")
    if pending.awaiting_id != player_id:
        raise GameRuleError("It is not your turn to respond.")
