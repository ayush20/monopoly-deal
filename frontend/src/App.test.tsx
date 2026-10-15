import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api", () => ({
  createGameSocket: () => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(),
  }),
}));

describe("App", () => {
  it("renders room entry", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Deal Room" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create room" })).toBeInTheDocument();
  });
});
