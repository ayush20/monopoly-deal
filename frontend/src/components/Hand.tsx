import { useState } from "react";

import type { RoomView, Send } from "../api";
import { ActionPanel } from "./ActionPanel";
import { CardChip } from "./CardChip";

type Props = { room: RoomView; send: Send; onError: (m: string) => void };

export function Hand({ room, send, onError }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const me = room.players.find((p) => p.id === room.you);
  const hand = me?.hand ?? [];
  const turn = room.turn;
  const canPlay =
    room.status === "in_progress" && room.pending === null && turn !== null &&
    turn.playerId === room.you && turn.phase === "active" && hand.length <= 7;
  const active = selected !== null && hand.includes(selected) ? selected : null;
  return (
    <section className="hand panel" aria-label="Your hand">
      <h2>Your hand ({hand.length})</h2>
      <div className="cards">
        {hand.length === 0 ? <p>Your cards appear here when the game starts.</p> : hand.map((id) => (
          <CardChip key={id} id={id} card={room.cards[id]} selected={id === active} onClick={() => setSelected(id === active ? null : id)} />
        ))}
      </div>
      {active !== null && <ActionPanel key={active} room={room} cardId={active} send={send} onError={onError} onDone={() => setSelected(null)} canPlay={canPlay} />}
      <TurnEnd room={room} send={send} onError={onError} />
    </section>
  );
}

function TurnEnd({ room, send, onError }: Props) {
  const [discards, setDiscards] = useState<string[]>([]);
  const me = room.players.find((p) => p.id === room.you);
  const hand = me?.hand ?? [];
  const turn = room.turn;
  if (room.status !== "in_progress" || turn === null || turn.playerId !== room.you || turn.phase === "awaiting_turn_start") return null;
  const excess = hand.length - 7;
  async function run(event: string, payload: Record<string, unknown>) {
    const error = await send(event, payload);
    if (error !== null) onError(error);
    else setDiscards([]);
  }
  if (excess > 0) {
    return (
      <div className="actions" aria-label="Discard">
        <h3>Discard {excess} card{excess === 1 ? "" : "s"}</h3>
        <div className="cards small">
          {hand.map((id) => (
            <CardChip key={id} id={id} card={room.cards[id]} selected={discards.includes(id)} onClick={() => setDiscards((d) => d.includes(id) ? d.filter((x) => x !== id) : [...d, id])} />
          ))}
        </div>
        <button type="button" disabled={discards.length !== excess || room.pending !== null} onClick={() => run("game:discard", { cardIds: discards })}>Discard selected</button>
      </div>
    );
  }
  return <button type="button" disabled={room.pending !== null} onClick={() => run("game:end_turn", {})}>End turn</button>;
}
