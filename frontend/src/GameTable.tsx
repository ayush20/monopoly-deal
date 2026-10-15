import type { RoomView, Send } from "./api";
import { Hand } from "./components/Hand";
import { HostControls } from "./components/HostControls";
import { PaymentPanel } from "./components/PaymentPanel";
import { PlayerBoard } from "./components/PlayerBoard";
import { ResponsePanel } from "./components/ResponsePanel";
import { StatusOverlay } from "./components/StatusOverlay";
import { TurnBanner } from "./components/TurnBanner";
import { WinnerScreen } from "./components/WinnerScreen";

type Props = { room: RoomView; send: Send; onError: (message: string) => void; onLeave: () => void };

export function GameTable({ room, send, onError, onLeave }: Props) {
  const players = room.players.filter((p) => p.active && !p.removed && p.bank !== undefined);
  const myTurnActive = room.turn?.playerId === room.you && room.turn.phase === "active" && room.pending === null && room.status === "in_progress";
  return (
    <div className="game">
      <TurnBanner room={room} send={send} onError={onError} />
      <ResponsePanel room={room} send={send} onError={onError} />
      <PaymentPanel room={room} send={send} onError={onError} />
      <section className="boards" aria-label="Table">
        {players.map((p) => <PlayerBoard key={p.id} player={p} room={room} send={send} onError={onError} canMove={myTurnActive} />)}
      </section>
      <Hand room={room} send={send} onError={onError} />
      <HostControls room={room} send={send} onError={onError} />
      <StatusOverlay room={room} />
      <WinnerScreen room={room} onLeave={onLeave} />
    </div>
  );
}
