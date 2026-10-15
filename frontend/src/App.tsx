import { FormEvent, useEffect, useState } from "react";
import type { Socket } from "socket.io-client";

import { createGameSocket, type RoomResult, type RoomView } from "./api";
import { GameTable } from "./GameTable";

function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [room, setRoom] = useState<RoomView | null>(null);
  const [notice, setNotice] = useState("Connect to create a private table.");

  useEffect(() => {
    const client = createGameSocket();
    setSocket(client);
    client.on("connect", () => setNotice("Realtime connection ready."));
    client.on("connect_error", () => setNotice("Realtime connection unavailable."));
    client.connect();
    return () => client.disconnect();
  }, []);

  function submit(event: FormEvent, command: "room:create" | "room:join") {
    event.preventDefault();
    if (socket === null) return;
    const payload = command === "room:create" ? { name } : { name, code };
    socket.emit(command, payload, (result: RoomResult) => {
      if ("error" in result) setNotice(result.error);
      else { setRoom(result.state); setNotice(`Room ${result.state.code} is ready.`); }
    });
  }

  if (room !== null) return <main className="table"><header><p className="eyebrow">Room code</p><h1>{room.code}</h1><p>{notice}</p></header><section className="players">{room.players.map((player) => <article className="player" key={player.id}><strong>{player.name}</strong>{player.host && <small> Host</small>}<p>{player.connected ? "Connected" : "Reconnecting…"}</p></article>)}</section><GameTable room={room} /></main>;

  return <main className="welcome"><section><p className="eyebrow">Private multiplayer card table</p><h1>Deal Room</h1><p>{notice}</p><form onSubmit={(event) => submit(event, "room:create")}><label>Name<input aria-label="Name" value={name} onChange={(event) => setName(event.target.value)} required /></label><button>Create room</button></form><form onSubmit={(event) => submit(event, "room:join")}><label>Room code<input aria-label="Room code" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} required /></label><button>Join room</button></form></section></main>;
}

export default App;
