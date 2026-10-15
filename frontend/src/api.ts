import { io } from "socket.io-client";

export type HealthResponse = {
  service: string;
  status: "ok";
};

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:5000";

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiUrl}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

export function createHealthSocket() {
  return io(apiUrl, { autoConnect: false });
}
