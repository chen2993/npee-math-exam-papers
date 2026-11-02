/**
 * The `?paper=<natural key>` hand-off from the search page and the reader.
 *
 * A search hit navigates to `/papers?paper=2024/math1/demo/7`; the catalogue must
 * open that paper's drawer and then drop the parameter so closing the drawer does
 * not reopen it. No composition context is provided: browsing must not need one.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { usePaperDrawer } from "./usePaperDrawer";

function Probe() {
  const drawer = usePaperDrawer();
  const location = useLocation();
  return (
    <>
      <span data-testid="detail">{drawer.detail?.natural_key ?? "none"}</span>
      <span data-testid="search">{location.search}</span>
    </>
  );
}

function renderRoute(initialEntry: string) {
  const router = createMemoryRouter(
    [{ path: "/papers", element: <Probe /> }],
    { initialEntries: [initialEntry] },
  );
  return render(<RouterProvider router={router} />);
}

describe("usePaperDrawer", () => {
  it("opens the requested paper and clears the parameter", async () => {
    renderRoute("/papers?paper=2024/math1/demo/7");

    expect(await screen.findByText("2024/math1/demo/7")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("search").textContent).toBe(""));
    // Still open after the parameter is dropped — that is the point of consuming it.
    expect(screen.getByTestId("detail").textContent).toBe("2024/math1/demo/7");
  });

  it("stays closed without a parameter", () => {
    renderRoute("/papers");
    expect(screen.getByTestId("detail").textContent).toBe("none");
  });

  it("ignores a malformed parameter", () => {
    renderRoute("/papers?paper=not-a-key");
    expect(screen.getByTestId("detail").textContent).toBe("none");
  });
});
