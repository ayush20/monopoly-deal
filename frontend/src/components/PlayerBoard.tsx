import { useState } from "react";

import { COLOR_LABEL, SET_SIZE, type Color, type PlayerView, type RoomView, type Send } from "../api";
import { CardChip } from "./CardChip";

function bankTotal(player: PlayerView, room: RoomView) {
  return (player.bank ?? []).reduce((sum, id) => sum + (room.cards[id]?.value ?? 0), 0);
}

function MoveWild({ id, room, send, onError }: { id: string; room: RoomView; send: Send; onError: (m: string) => void }) {
  const [color, setColor] = useState<Color | "">("");
  const card = room.cards[id];
  if (card === undefined || card.type !== "property_wild") return null;
  return (
    <span className="row">
      <select aria-label={`Move ${card.name} to`} value={color} onChange={(e) => setColor(e.target.value as Color)}>
        <option value="">Move to…</option>
        {card.colors.map((c) => <option key={c} value={c}>{COLOR_LABEL(c)}</option>)}
      </select>
      <button type="button" disabled={color === ""} onClick={async () => {
        const error = await send("game:move_wild", { cardId: id, color });
        if (error !== null) onError(error);
      }}>Move</button>
    </span>
  );
}

type Props = { player: PlayerView; room: RoomView; send: Send; onError: (m: string) => void; canMove: boolean };

export function PlayerBoard({ player, room, send, onError, canMove }: Props) {
  const mine = player.id === room.you;
  const sets = Object.entries(player.properties ?? {}).filter(([, ids]) => ids.length > 0) as [Color, string[]][];
  return (
    <article className="board" data-testid={`board-${player.id}`}>
      <h3>
        {player.name}{mine ? " (you)" : ""}
        {room.turn?.playerId === player.id && <span className="badge ok">Turn</span>}
        {!player.connected && <span className="badge warn">Offline</span>}
      </h3>
      <p>
        Bank {bankTotal(player, room)}M · Hand {player.handCount ?? 0} · Sets {player.completedSets ?? 0}/3
      </p>
      {sets.length === 0 ? <p className="muted">No properties</p> : (
        <ul className="sets">
          {sets.map(([color, ids]) => {
            const improvements = player.improvements?.[color] ?? [];
            return (
              <li key={color} data-color={color}>
                <strong>{COLOR_LABEL(color)}: {ids.length} of {SET_SIZE[color]}</strong>
                {improvements.length > 0 && <small> + {improvements.map((i) => room.cards[i]?.name ?? i).join(", ")}</small>}
                <div className="cards small">
                  {ids.map((id) => (
                    <span key={id}>
                      <CardChip id={id} card={room.cards[id]} />
                      {mine && canMove && <MoveWild id={id} room={room} send={send} onError={onError} />}
                    </span>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}
