"""Strict payment selection and transfer rules for debt obligations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .cards import SET_SIZE, Color
from .errors import GameRuleError
from .game import GameState, PlayerState


class AssetLocation(StrEnum):
    BANK = "bank"
    PROPERTY = "property"
    IMPROVEMENT = "improvement"


@dataclass(frozen=True, slots=True)
class PaymentAsset:
    """A card that may legally be selected to settle a debt."""

    card_id: str
    location: AssetLocation
    value: int
    color: Color | None = None


def available_payment_assets(state: GameState, payer_id: str) -> list[PaymentAsset]:
    """List every non-zero-value card laid down by a player.

    Hand cards are never available for payment. The two multicolour wild cards
    intentionally have no value and are excluded.
    """
    payer = state.player(payer_id)
    assets: list[PaymentAsset] = []
    for card_id in payer.bank:
        assets.append(_asset(state, card_id, AssetLocation.BANK))
    for color, card_ids in payer.properties.items():
        for card_id in card_ids:
            assets.append(_asset(state, card_id, AssetLocation.PROPERTY, color))
    for color, card_ids in payer.improvements.items():
        for card_id in card_ids:
            assets.append(_asset(state, card_id, AssetLocation.IMPROVEMENT, color))
    return [asset for asset in assets if asset.value > 0]


def settle_payment(
    state: GameState,
    *,
    payer_id: str,
    recipient_id: str,
    amount: int,
    card_ids: list[str],
) -> int:
    """Validate and transfer a chosen strict-payment bundle.

    A payer may overpay and never receives change. If their available laid-card
    value is below the debt, they must surrender every available payment asset.
    """
    if amount <= 0:
        raise GameRuleError("A payment amount must be positive.")
    if payer_id == recipient_id:
        raise GameRuleError("A player cannot pay themselves.")
    payer = state.player(payer_id)
    recipient = state.player(recipient_id)
    if len(card_ids) != len(set(card_ids)):
        raise GameRuleError("A payment card can be selected only once.")

    available = {asset.card_id: asset for asset in available_payment_assets(state, payer_id)}
    if any(card_id not in available for card_id in card_ids):
        raise GameRuleError("Payments may use only laid cards with a cash value.")
    selected = [available[card_id] for card_id in card_ids]
    selected_total = sum(asset.value for asset in selected)
    available_total = sum(asset.value for asset in available.values())

    if available_total < amount:
        if set(card_ids) != set(available):
            raise GameRuleError("A player who cannot cover a debt must pay all available assets.")
    elif selected_total < amount:
        raise GameRuleError("The selected cards do not cover the debt.")

    for asset in selected:
        _transfer_asset(state, payer, recipient, asset)
    return selected_total


def _asset(
    state: GameState,
    card_id: str,
    location: AssetLocation,
    color: Color | None = None,
) -> PaymentAsset:
    value = state.cards[card_id].value
    return PaymentAsset(card_id=card_id, location=location, value=value or 0, color=color)


def _transfer_asset(
    state: GameState,
    payer: PlayerState,
    recipient: PlayerState,
    asset: PaymentAsset,
) -> None:
    if asset.location is AssetLocation.BANK:
        payer.bank.remove(asset.card_id)
        recipient.bank.append(asset.card_id)
        return

    if asset.location is AssetLocation.IMPROVEMENT:
        assert asset.color is not None
        payer.improvements[asset.color].remove(asset.card_id)
        recipient.bank.append(asset.card_id)
        return

    assert asset.color is not None
    payer.properties[asset.color].remove(asset.card_id)
    recipient.properties.setdefault(asset.color, []).append(asset.card_id)
    _bank_orphaned_improvements(state, payer, asset.color)


def _bank_orphaned_improvements(state: GameState, payer: PlayerState, color: Color) -> None:
    """Return improvements to the owner's bank if their underlying set breaks."""
    if len(payer.properties.get(color, [])) >= SET_SIZE[color]:
        return
    payer.bank.extend(payer.improvements.pop(color, []))
