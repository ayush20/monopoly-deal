import { useState } from "react";

import type { RoomView, Send } from "../api";
import { CardChip } from "./CardChip";

export function PaymentPanel({ room, send, onError }: { room: RoomView; send: Send; onError: (m: string) => void }) {
  const [chosen, setChosen] = useState<string[]>([]);
  const { pending } = room;
  const me = room.players.find((p) => p.id === room.you);
  if (pending === null || pending.stage !== "payment" || pending.payment === null || pending.awaitingId !== room.you || me === undefined) return null;
  const { amount, recipientId } = pending.payment;
  const recipient = room.players.find((p) => p.id === recipientId)?.name ?? "someone";
  const options = [
    ...(me.bank ?? []),
    ...Object.values(me.properties ?? {}).flatMap((ids) => ids ?? []),
    ...Object.values(me.improvements ?? {}).flatMap((ids) => ids ?? []),
  ].filter((id) => room.cards[id]?.value != null);
  const total = chosen.reduce((sum, id) => sum + (room.cards[id]?.value ?? 0), 0);
  const toggle = (id: string) => setChosen((c) => c.includes(id) ? c.filter((x) => x !== id) : [...c, id]);
  async function pay() {
    const error = await send("game:pay", { cardIds: chosen });
    if (error !== null) onError(error);
    else setChosen([]);
  }
  return (
    <section className="panel payment" aria-label="Payment">
      <h2>Pay {amount}M to {recipient}</h2>
      <p>Selected {total}M of {amount}M. The server enforces strict payment rules (no overpaying with unneeded cards).</p>
      <div className="cards small">
        {options.map((id) => <CardChip key={id} id={id} card={room.cards[id]} selected={chosen.includes(id)} onClick={() => toggle(id)} />)}
      </div>
      <button type="button" onClick={pay}>Pay selected</button>
    </section>
  );
}
