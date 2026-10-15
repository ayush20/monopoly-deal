import type { RoomView, Send } from "../api";

export function TurnBanner({ room, send, onError }: { room: RoomView; send: Send; onError: (m: string) => void }) {
  const { turn } = room;
  if (turn === null) return null;
  const mine = turn.playerId === room.you;
  const name = room.players.find((p) => p.id === turn.playerId)?.name ?? "Someone";
  const text = mine
    ? turn.phase === "awaiting_turn_start"
      ? "Your turn — draw to begin"
      : `Your turn, ${turn.playsUsed} of ${turn.playsMax} plays used`
    : `${name}'s turn, ${turn.playsUsed} of ${turn.playsMax} plays used`;
  async function run(event: string) {
    const error = await send(event, {});
    if (error !== null) onError(error);
  }
  const canDraw = mine && room.status === "in_progress" && turn.phase === "awaiting_turn_start";
  return (
    <div className="banner" role="status">
      <strong>{text}</strong>
      <span>Draw pile {room.drawCount ?? 0} · Discard {room.discardCount ?? 0}{room.discardTop ? ` (top: ${room.cards[room.discardTop]?.name ?? room.discardTop})` : ""}</span>
      {canDraw && <button type="button" onClick={() => run("game:start_turn")}>Draw cards</button>}
    </div>
  );
}
