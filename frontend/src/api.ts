import { io } from "socket.io-client";

export type Color =
  | "brown" | "light_blue" | "pink" | "orange" | "red"
  | "yellow" | "green" | "dark_blue" | "railroad" | "utility";

export type CardType = "money" | "property" | "property_wild" | "rent" | "action";
export type ActionKind =
  | "deal_breaker" | "forced_deal" | "sly_deal" | "just_say_no" | "debt_collector"
  | "birthday" | "double_rent" | "house" | "hotel" | "pass_go";

export type Card = {
  id: string;
  name: string;
  type: CardType;
  value: number | null;
  colors: Color[];
  action: ActionKind | null;
};

export type PlayerView = {
  id: string;
  name: string;
  host: boolean;
  ready: boolean;
  active: boolean;
  connected: boolean;
  removed: boolean;
  reservationSeconds: number | null;
  bank?: string[];
  properties?: Partial<Record<Color, string[]>>;
  improvements?: Partial<Record<Color, string[]>>;
  handCount?: number;
  completedSets?: number;
  hand?: string[];
};

export type TurnView = {
  playerId: string;
  phase: "awaiting_turn_start" | "active" | "complete";
  playsUsed: number;
  playsMax: number;
};

export type PendingKind = "sly_deal" | "forced_deal" | "deal_breaker" | "debt_collector" | "birthday" | "rent";

export type PendingView = {
  kind: PendingKind;
  stage: "response" | "payment";
  initiatorId: string;
  cardIds: string[];
  targets: string[];
  params: Record<string, unknown>;
  awaitingId: string;
  currentTargetId: string | null;
  cancelled: boolean;
  payment: null | {
    payerId: string;
    recipientId: string;
    amount: number;
    reason: string;
    queue: { payerId: string; amount: number }[];
  };
};

export type RoomView = {
  code: string;
  status: "lobby" | "in_progress" | "paused" | "ended";
  you: string;
  players: PlayerView[];
  turn: TurnView | null;
  drawCount: number | null;
  discardTop: string | null;
  discardCount: number | null;
  winner: string | null;
  pending: PendingView | null;
  cards: Record<string, Card>;
};

export type RoomResult = { ok: true; token: string; state: RoomView } | { error: string };
export type Ack = { ok: true } | { error: string };

/** Sends a command; resolves to an error message, or null on success. */
export type Send = (event: string, payload?: Record<string, unknown>) => Promise<string | null>;

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:5001";

export function createGameSocket() {
  return io(apiUrl, { autoConnect: false });
}

const LAST_ROOM_KEY = "deal-room:last-room";
const tokenKey = (code: string) => `deal-room:token:${code}`;

export function saveSession(code: string, token: string) {
  localStorage.setItem(tokenKey(code), token);
  localStorage.setItem(LAST_ROOM_KEY, code);
}

export function loadSession(): { code: string; token: string } | null {
  const code = localStorage.getItem(LAST_ROOM_KEY);
  if (code === null) return null;
  const token = localStorage.getItem(tokenKey(code));
  return token === null ? null : { code, token };
}

export function clearSession(code: string) {
  localStorage.removeItem(tokenKey(code));
  if (localStorage.getItem(LAST_ROOM_KEY) === code) localStorage.removeItem(LAST_ROOM_KEY);
}

export const SET_SIZE: Record<Color, number> = {
  brown: 2, light_blue: 3, pink: 3, orange: 3, red: 3,
  yellow: 3, green: 3, dark_blue: 2, railroad: 4, utility: 2,
};

export const COLOR_LABEL = (color: string) => color.replaceAll("_", " ");
