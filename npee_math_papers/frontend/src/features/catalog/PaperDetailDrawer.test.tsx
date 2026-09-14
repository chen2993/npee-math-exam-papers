/**
 * The paper drawer is the main reading surface, so its two modal obligations are
 * worth pinning down: Escape closes it, and the page behind it does not scroll.
 * The "join the composition" action must also be reachable without going back to
 * the row the user came from.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CatalogGateway } from "../../application/catalog/ports";
import { CompositionWorkspaceProvider } from "../../app/CompositionWorkspace";
import type { PaperSummary } from "../../domain/catalog/models";
import { ToastProvider } from "../../shared/ui";
import { PaperDetailDrawer } from "./PaperDetailDrawer";

const paper: PaperSummary = {
  natural_key: "2024/math1/demo/1",
  bundle: "demo-2024-math1",
  series_key: "demo",
  series_name: "示例系列",
  year: 2024,
  subject: "math1",
  paper_no: 1,
  question_count: 1,
  section_counts: {},
  content_hash: "abc",
};

const gateway = {
  getPaper: vi.fn(async () => ({
    // The real endpoint returns the canonical document plus a derived `meta`
    // block, so the stub has to match that shape or the test proves nothing.
    schema_version: "3.0",
    paper: {
      series_key: paper.series_key,
      year: paper.year,
      subject: paper.subject,
      paper_no: paper.paper_no,
    },
    meta: { ...paper, question_count: 1 },
    questions: [
      {
        number: 1,
        section: "choice" as const,
        points: 5,
        stem: { text: "设 $f(x)=x$，则 $f'(1)=$", figures: [] },
        choices: [
          { label: "A", text: "$0$", figures: [] },
          { label: "B", text: "$1$", figures: [] },
        ],
      },
    ],
  })),
} as unknown as CatalogGateway;

const repository = { load: () => [], save: () => {} };
const exportGateway = { jobs: async () => [] } as never;

function renderDrawer(onClose = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <CompositionWorkspaceProvider repository={repository} exportGateway={exportGateway}>
          <PaperDetailDrawer paper={paper} gateway={gateway} onClose={onClose} />
        </CompositionWorkspaceProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
  return { onClose };
}

/** Wait for the drawer's content to render (KaTeX output is async-ish). */
async function findLoaded() {
  // The header action is stable, unlike the KaTeX tree; question cards follow it.
  await screen.findByText(/共 1 题/);
}

describe("PaperDetailDrawer", () => {
  it("renders the fetched questions", async () => {
    renderDrawer();
    await findLoaded();
    expect(document.querySelector(".question-card")).toBeTruthy();
    expect(document.querySelectorAll(".question-choice")).toHaveLength(2);
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDrawer();
    await findLoaded();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("locks background scrolling while open and restores it on close", async () => {
    const { unmount } = render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ToastProvider>
          <CompositionWorkspaceProvider repository={repository} exportGateway={exportGateway}>
            <PaperDetailDrawer paper={paper} gateway={gateway} onClose={vi.fn()} />
          </CompositionWorkspaceProvider>
        </ToastProvider>
      </QueryClientProvider>,
    );
    await waitFor(() => expect(document.body.style.overflow).toBe("hidden"));
    unmount();
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  it("adds the paper to the active draft from the header", async () => {
    const user = userEvent.setup();
    renderDrawer();
    await findLoaded();
    await user.click(screen.getByRole("button", { name: "加入组卷" }));
    expect(await screen.findByRole("button", { name: "已加入" })).toBeInTheDocument();
  });
});
