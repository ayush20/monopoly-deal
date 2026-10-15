import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { Card, PlayerView, RoomView } from "./api";

type Handler = (...args: unknown[]) => void;
const handlers: Record<string, Handler> = {};
const emit = vi.fn();

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  createGameSocket: () => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    emit,
    on: (event: string, handler: Handler) => { handlers[event] = handler; },
  }),
}));

const player = (id: string, over: Partial<PlayerView> = {}): PlayerView => ({
  id, name: id, host: false, ready: false, active: false, connected: true,
  removed: false, reservationSeconds: null, ...over,
});

const base = (over: Partial<RoomView>): RoomView => ({
  code: "ABC123", status: "lobby", you: "a", players: [], turn: null, drawCount: null,
  discardTop: null, discardCount: null, winner: null, pending: null, cards: {}, ...over,
});

function push(state: RoomView) {
  act(() => handlers["room:state"](state));
}

beforeEach(() => {
  localStorage.clear();
  emit.mockReset();
});

describe("App", () => {
  it("renders room entry", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Deal Room" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create room" })).toBeInTheDocument();
  });

  it("reconnects with the stored token on connect", () => {
    localStorage.setItem("deal-room:last-room", "ABC123");
    localStorage.setItem("deal-room:token:ABC123", "tok");
    render(<App />);
    act(() => handlers.connect());
    expect(emit).toHaveBeenCalledWith("room:reconnect", { code: "ABC123", token: "tok" }, expect.any(Function));
  });

  it("shows Start only to the host, enabled once two are ready", () => {
    render(<App />);
    const host = (ready: boolean) => [player("a", { host: true, ready }), player("b", { ready: true })];
    push(base({ players: host(false) }));
    expect(screen.getByRole("button", { name: "Start game" })).toBeDisabled();
    push(base({ players: host(true) }));
    const start = screen.getByRole("button", { name: "Start game" });
    expect(start).toBeEnabled();
    fireEvent.click(start);
    expect(emit).toHaveBeenCalledWith("room:start", {}, expect.any(Function));
  });

  it("hides Start from non-hosts and toggles ready", () => {
    render(<App />);
    push(base({ you: "b", players: [player("a", { host: true, ready: true }), player("b", { ready: true })] }));
    expect(screen.queryByRole("button", { name: "Start game" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Not ready" }));
    expect(emit).toHaveBeenCalledWith("room:ready", { ready: false }, expect.any(Function));
  });

  it("offers bank and property actions for the selected hand card", () => {
    const cards: Record<string, Card> = {
      m1: { id: "m1", name: "Money 3", type: "money", value: 3, colors: [], action: null },
      p1: { id: "p1", name: "Brown Property", type: "property", value: 1, colors: ["brown"], action: null },
    };
    render(<App />);
    push(base({
      status: "in_progress", cards, drawCount: 90, discardCount: 0,
      turn: { playerId: "a", phase: "active", playsUsed: 1, playsMax: 3 },
      players: [
        player("a", { host: true, active: true, bank: [], properties: {}, handCount: 2, completedSets: 0, hand: ["m1", "p1"] }),
        player("b", { active: true, bank: [], properties: {}, handCount: 5, completedSets: 0 }),
      ],
    }));
    expect(screen.getByText("Your turn, 1 of 3 plays used")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Money 3/ }));
    fireEvent.click(screen.getByRole("button", { name: "Bank" }));
    expect(emit).toHaveBeenCalledWith("game:bank", { cardId: "m1" }, expect.any(Function));
    fireEvent.click(screen.getByRole("button", { name: /Brown Property/ }));
    expect(screen.queryByRole("button", { name: "Bank" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Play as property" }));
    expect(emit).toHaveBeenCalledWith("game:play_property", { cardId: "p1", color: "brown" }, expect.any(Function));
  });

  it("disables plays when it is not your turn", () => {
    const cards: Record<string, Card> = {
      m1: { id: "m1", name: "Money 3", type: "money", value: 3, colors: [], action: null },
    };
    render(<App />);
    push(base({
      status: "in_progress", cards,
      turn: { playerId: "b", phase: "active", playsUsed: 0, playsMax: 3 },
      players: [
        player("a", { active: true, bank: [], properties: {}, hand: ["m1"] }),
        player("b", { active: true, bank: [], properties: {} }),
      ],
    }));
    fireEvent.click(screen.getByRole("button", { name: /Money 3/ }));
    expect(screen.getByRole("button", { name: "Bank" })).toBeDisabled();
  });
});
