import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { AuthProvider } from "./auth";
import { HeatmapTab } from "./pages/HeatmapTab";
import { IntelligenceTab } from "./pages/IntelligenceTab";

const BUNDLE = {
  assets: [
    { id: "a1", vec: [1, 0, 0], tags: ["minimal"], caption: "minimal", type: "text" },
    { id: "a2", vec: [0, 1, 0], tags: ["street"], caption: "street", type: "text" },
  ],
  regions: [{ id: "region_0", label: "Minimal", memberIds: ["a1"], centroid: [1, 0, 0] }],
};

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async () => ({ json: async () => BUNDLE }) as any));
});

describe("App routes", () => {
  it("renders the landing brand and CTA", () => {
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(screen.getAllByText("TasteGraph").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Open dashboard/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/A taste graph builders can query/i)).toBeInTheDocument();
  });

  it("redirects /dashboard to /login when unauthenticated", async () => {
    window.history.pushState({}, "", "/dashboard");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});

describe("HeatmapTab", () => {
  it("renders the sidebar heading and loads the bundle", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <HeatmapTab />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("Taste heatmap")).toBeInTheDocument();
    expect(screen.getByTestId("heatmap-tab")).toBeInTheDocument();
  });
});

describe("IntelligenceTab", () => {
  it("shows connect empty state in local / unauthed mode", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <IntelligenceTab />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("intelligence-tab")).toBeInTheDocument();
    expect(screen.getByText(/Connect to a server/i)).toBeInTheDocument();
  });
});

describe("Login", () => {
  it("offers connect and local mode", async () => {
    const { Login } = await import("./pages/Login");
    render(
      <MemoryRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText(/Connect to server/i)).toBeInTheDocument();
    expect(screen.getByText(/Continue in local mode/i)).toBeInTheDocument();
  });
});
