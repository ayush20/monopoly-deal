import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { Socket } from "socket.io-client";

import {
  clearSession, createGameSocket, loadSession, saveSession,
  type RoomResult, type RoomView, type Send,
} from "./api";
import { GameTable } from "./GameTable";
import { Lobby } from "./components/Lobby";

function App() {
  const socketRef = useRef<Socket | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [room, setRoom] = useState<RoomView | null>(null);
  const [notice, setNotice] = useState("Connect to create a private table.");

  useEffect(() => {
    const client = createGameSocket();
    socketRef.current = client;
    client.on("room:state", (state: RoomView) => setRoom(state));
    client.on("connect", () => {
      setNotice("Realtime connection ready.");
      const session = loadSession();
      if (session === null) return;
      client.emit("room:reconnect", session, (result: RoomResult) => {
        if ("error" in result) {
          clearSession(session.code);
          setRoom(null);
          setNotice(result.error);
        } else {
          saveSession(result.state.code, result.token);
          setRoom(result.state);
        }
      });
    });
    client.on("connect_error", () => setNotice("Realtime connection unavailable."));
    client.connect();
    return () => {
      client.disconnect();
    };
  }, []);

  const send = useCallback<Send>((event, payload = {}) => new Promise((resolve) => {
    const client = socketRef.current;
    if (client === null) return resolve("Not connected.");
    client.emit(event, payload, (result: { ok?: boolean; error?: string }) => {
      resolve(result?.error ?? null);
    });
  }), []);

  function submit(event: FormEvent, command: "room:create" | "room:join") {
    event.preventDefault();
    const client = socketRef.current;
    if (client === null) return;
    const payload = command === "room:create" ? { name } : { name, code };
    client.emit(command, payload, (result: RoomResult) => {
      if ("error" in result) setNotice(result.error);
      else {
        saveSession(result.state.code, result.token);
        setRoom(result.state);
        setNotice(`Room ${result.state.code} is ready.`);
      }
    });
  }

  function leave() {
    if (room !== null) clearSession(room.code);
    setRoom(null);
    setNotice("Create or join a table.");
  }

  if (room !== null) {
    return (
      <main className="table">
        <header>
          <p className="eyebrow">Room code</p>
          <h1>{room.code}</h1>
          <p role="status">{notice}</p>
        </header>
        {room.status === "lobby"
          ? <Lobby room={room} send={send} onError={setNotice} />
          : <GameTable room={room} send={send} onError={setNotice} onLeave={leave} />}
      </main>
    );
  }

  return (
    <main className="welcome">
      <section>
        <p className="eyebrow">Private multiplayer card table</p>
        <h1>Deal Room</h1>
        <p>{notice}</p>
        <form onSubmit={(event) => submit(event, "room:create")}>
          <label>Name<input aria-label="Name" value={name} onChange={(event) => setName(event.target.value)} required /></label>
          <button>Create room</button>
        </form>
        <form onSubmit={(event) => submit(event, "room:join")}>
          <label>Room code<input aria-label="Room code" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} required /></label>
          <button>Join room</button>
        </form>
      </section>
    </main>
  );
}

export default App;
