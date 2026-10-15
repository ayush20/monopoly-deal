import { useMemo, useState } from "react";

import type { RoomView } from "./api";

export function GameTable({ room }: { room: RoomView }) {
  const [selected, setSelected] = useState<string | null>(null);
  const hand = useMemo(() => room.players.flatMap((player) => player.hand ?? []), [room]);
  return <><section className="panel"><h2>{room.status === "lobby" ? "Lobby" : "Game table"}</h2><p>Tap a card, then choose an available action or target. The server validates every move.</p><button disabled={selected === null}>Play selected card</button><button onClick={() => setSelected(null)}>Clear selection</button></section><section className="hand"><h2>Your hand</h2><div className="cards">{hand.length ? hand.map((card) => <button className={selected === card ? "card selected" : "card"} key={card} onClick={() => setSelected(card)}><small>DEAL</small><strong>{card.replaceAll("-", " ")}</strong></button>) : <p>Your cards appear here when the game starts.</p>}</div></section></>;
}
