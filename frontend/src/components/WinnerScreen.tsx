import type { RoomView } from "../api";

export function WinnerScreen({ room, onLeave }: { room: RoomView; onLeave: () => void }) {
  if (room.status !== "ended") return null;
  const winner = room.players.find((p) => p.id === room.winner);
  return (
    <div className="overlay" role="dialog" aria-label="Game over">
      <div className="panel">
        <h2>Game over</h2>
        <p>{winner ? (winner.id === room.you ? "You win!" : `${winner.name} wins!`) : "The host ended the game."}</p>
        <button type="button" onClick={onLeave}>Back to start</button>
      </div>
    </div>
  );
}
