import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api", () => ({
  createHealthSocket: () => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(),
  }),
  fetchHealth: () => Promise.resolve({ service: "deal-room-api", status: "ok" }),
}));

describe("App", () => {
  it("renders the foundation service checks", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Deal Room" })).toBeInTheDocument();
    expect(screen.getByTestId("api-status")).toHaveTextContent("checking");
    expect(screen.getByTestId("socket-status")).toHaveTextContent("checking");
  });
});
