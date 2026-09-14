/**
 * The `?paper=<natural key>` hand-off between the search page and the catalogue.
 *
 * A search hit navigates to `/papers?paper=2024/math1/demo/7`; the catalogue must
 * open that paper's drawer and then drop the parameter so closing the drawer
 * does not reopen it.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CompositionWorkspaceProvider } from "../../app/CompositionWorkspace";
import { useCatalogSelection } from "./useCatalogSelection";

const repository = { load: () => [], save: () => {} };
const exportGateway = { jobs: async () => [] } as never;

function Probe() {
  const selection = useCatalogSelection();
  const location = useLocation();
  return (
    <>
      <span data-testid="detail">{selection.detail?.natural_key ?? "none"}</span>
      <span data-testid="search">{location.search}</span>
    </>
  );
}

function renderRoute(initialEntry: string) {
  const router = createMemoryRouter(
    [
      {
        path: "/papers",
        element: (
          <CompositionWorkspaceProvider repository={repository} exportGateway={exportGateway}>
            <Probe />
          </CompositionWorkspaceProvider>
        ),
      },
    ],
    { initialEntries: [initialEntry] },
  );
  render(<RouterProvider router={router} />);
}

describe("useCatalogSelection", () => {
  it("opens the drawer for a deep-linked paper", async () => {
    renderRoute("/papers?paper=2024%2Fmath1%2Fdemo%2F7");
    await waitFor(() => expect(screen.getByTestId("detail")).toHaveTextContent("2024/math1/demo/7"));
  });

  it("drops the parameter so closing the drawer does not reopen it", async () => {
    renderRoute("/papers?paper=2024%2Fmath1%2Fdemo%2F7&series=demo");
    await waitFor(() => expect(screen.getByTestId("search")).not.toHaveTextContent("paper="));
    // The unrelated filters survive the rewrite.
    expect(screen.getByTestId("search")).toHaveTextContent("series=demo");
    expect(screen.getByTestId("detail")).toHaveTextContent("2024/math1/demo/7");
  });

  it("ignores a malformed paper parameter", async () => {
    renderRoute("/papers?paper=garbage");
    // The bad key is simply not a paper: no drawer, and the app keeps running.
    await waitFor(() => expect(screen.getByTestId("search")).toBeInTheDocument());
    expect(screen.getByTestId("detail")).toHaveTextContent("none");
  });

  it("leaves the drawer closed when no paper is requested", async () => {
    renderRoute("/papers");
    // Await the workspace provider's mount effect so it settles inside act().
    await waitFor(() => expect(screen.getByTestId("search")).toBeInTheDocument());
    expect(screen.getByTestId("detail")).toHaveTextContent("none");
  });
});
