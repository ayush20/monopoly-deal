import type { RoomView, Send } from "../api";

export function HostControls({ room, send, onError }: { room: RoomView; send: Send; onError: (m: string) => void }) {
  const me = room.players.find((p) => p.id === room.you);
  if (me?.host !== true || room.status === "lobby" || room.status === "ended") return null;
  async function run(event: string, payload: Record<string, unknown> = {}) {
    const error = await send(event, payload);
    if (error !== null) onError(error);
  }
  return (
    <section className="panel host" aria-label="Host controls">
      <h2>Host controls</h2>
      <div className="row">
        <button type="button" disabled={room.status !== "in_progress"} onClick={() => run("room:pause")}>Pause</button>
        <button type="button" disabled={room.status !== "paused"} onClick={() => run("room:resume")}>Resume</button>
        <button type="button" onClick={() => run("room:end")}>End game</button>
      </div>
      <ul className="lobby-list">
        {room.players.filter((p) => p.id !== room.you && !p.removed).map((p) => (
          <li key={p.id}><span>{p.name}</span><button type="button" onClick={() => run("room:remove", { targetId: p.id })}>Remove {p.name}</button></li>
        ))}
      </ul>
    </section>
  );
}
