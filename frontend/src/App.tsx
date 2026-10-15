import { useEffect, useState } from "react";
import type { Socket } from "socket.io-client";

import { createHealthSocket, fetchHealth } from "./api";

type CheckState = "checking" | "ready" | "unavailable";

function App() {
  const [apiState, setApiState] = useState<CheckState>("checking");
  const [socketState, setSocketState] = useState<CheckState>("checking");

  useEffect(() => {
    let active = true;
    const socket: Socket = createHealthSocket();

    void fetchHealth()
      .then(() => active && setApiState("ready"))
      .catch(() => active && setApiState("unavailable"));

    socket.on("connect", () => active && setSocketState("ready"));
    socket.on("connect_error", () => active && setSocketState("unavailable"));
    socket.connect();

    return () => {
      active = false;
      socket.disconnect();
    };
  }, []);

  return (
    <main>
      <section aria-labelledby="page-title">
        <p className="eyebrow">Foundation check</p>
        <h1 id="page-title">Deal Room</h1>
        <p>A real-time card-table experience is being prepared.</p>
        <dl>
          <div>
            <dt>API health</dt>
            <dd data-testid="api-status">{apiState}</dd>
          </div>
          <div>
            <dt>Realtime connection</dt>
            <dd data-testid="socket-status">{socketState}</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}

export default App;
