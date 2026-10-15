import { useEffect, useState } from "react";

import type { RoomView } from "../api";

function format(seconds: number) {
  const m = Math.floor(seconds / 60);
  return `${m}:${String(seconds % 60).padStart(2, "0")}`;
}

function Countdown({ name, seconds }: { name: string; seconds: number }) {
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    const timer = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(timer);
  }, []);
  return <li>{name} can rejoin for <strong>{format(left)}</strong></li>;
}

export function StatusOverlay({ room }: { room: RoomView }) {
  if (room.status !== "paused") return null;
  const away = room.players.filter((p) => !p.connected && !p.removed && p.reservationSeconds !== null);
  return (
    <div className="overlay" role="alertdialog" aria-label="Game paused">
      <div className="panel">
        <h2>Game paused</h2>
        <p>A player disconnected. The host can resume once everyone is back or remove them.</p>
        <ul>{away.map((p) => <Countdown key={`${p.id}-${p.reservationSeconds}`} name={p.name} seconds={p.reservationSeconds ?? 0} />)}</ul>
      </div>
    </div>
  );
}
