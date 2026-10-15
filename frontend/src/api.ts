import { io } from "socket.io-client";

export type PlayerView = { id: string; name: string; host: boolean; ready: boolean; active: boolean; connected: boolean; removed: boolean; hand?: string[]; bank?: string[]; properties?: Record<string, string[]> };
export type RoomView = { code: string; status: "lobby" | "in_progress" | "paused" | "ended"; players: PlayerView[] };
export type RoomResult = { token: string; state: RoomView } | { error: string };

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:5001";

export function createGameSocket() {
  return io(apiUrl, { autoConnect: false });
}
