import type { RoomView, Send } from "../api";

export function Lobby({ room, send, onError }: { room: RoomView; send: Send; onError: (message: string) => void }) {
  const me = room.players.find((player) => player.id === room.you);
  const isHost = me?.host === true;
  const readyCount = room.players.filter((player) => player.ready && !player.removed).length;
  const canStart = isHost && room.status === "lobby" && readyCount >= 2;

  async function run(event: string, payload: Record<string, unknown> = {}) {
    const error = await send(event, payload);
    if (error !== null) onError(error);
  }

  return (
    <section className="panel" aria-label="Lobby">
      <h2>Lobby</h2>
      <p>Share code <strong>{room.code}</strong>. {readyCount} of {room.players.length} ready; at least 2 must be ready to start.</p>
      <ul className="lobby-list">
        {room.players.filter((player) => !player.removed).map((player) => (
          <li key={player.id}>
            <span>{player.name}{player.host ? " (host)" : ""}{player.id === room.you ? " (you)" : ""}</span>
            <span className={player.ready ? "badge ok" : "badge"}>{player.ready ? "Ready" : "Not ready"}</span>
          </li>
        ))}
      </ul>
      <div className="row">
        <button type="button" onClick={() => run("room:ready", { ready: !(me?.ready ?? false) })}>
          {me?.ready ? "Not ready" : "Ready"}
        </button>
        {isHost && <button type="button" disabled={!canStart} onClick={() => run("room:start")}>Start game</button>}
      </div>
    </section>
  );
}
