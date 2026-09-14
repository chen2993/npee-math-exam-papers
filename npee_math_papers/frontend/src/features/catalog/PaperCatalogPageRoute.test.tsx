/**
 * Catalogue behaviour that is easy to regress and invisible to a type check:
 * the bulk "add this page" action, the select-all toggle, and the fact that the
 * search box is sent to the *server* rather than filtering the loaded page.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { CatalogGateway, PaperQuery } from "../../application/catalog/ports";
import { AppServicesProvider } from "../../app/AppServices";
import { CompositionWorkspaceProvider } from "../../app/CompositionWorkspace";
import type { PaperPage, PaperSummary } from "../../domain/catalog/models";
import { PreferencesProvider } from "../../preferences";
import { ToastProvider } from "../../shared/ui";
import PaperCatalogPageRoute from "./PaperCatalogPageRoute";

function paper(no: number): PaperSummary {
  return {
    natural_key: `2024/math1/demo/${no}`,
    bundle: "demo-2024-math1",
    series_key: "demo",
    series_name: "示例系列",
    year: 2024,
    subject: "math1",
    paper_no: no,
    question_count: 22,
    section_counts: {},
    content_hash: "abc",
  };
}

function gatewayWith(papers: PaperSummary[]): { gateway: CatalogGateway; queries: PaperQuery[] } {
  const queries: PaperQuery[] = [];
  const gateway: CatalogGateway = {
    overview: vi.fn(async () => ({
      stats: { bundles: 1, papers: papers.length, questions: 0, figures: 0, series: ["demo"], years: [2024], subjects: ["math1"] },
      series: [{ series_key: "demo", series_name: "示例系列", paper_count: papers.length, question_count: 0, years: [2024], subjects: ["math1"] }],
      bundles: [],
    })),
    listSeries: vi.fn(async () => []),
    listBundles: vi.fn(async () => []),
    listPapers: vi.fn(async (query: PaperQuery): Promise<PaperPage> => {
      queries.push(query);
      return { total: papers.length, offset: 0, count: papers.length, papers };
    }),
    // The catalogue only reads the three endpoints above; the rest exist to
    // satisfy the port and are never called from this page.
    getPaper: vi.fn(),
    search: vi.fn(),
    getQuestion: vi.fn(),
    releaseManifest: vi.fn(),
    listLogs: vi.fn(),
    clearLogs: vi.fn(),
  } as unknown as CatalogGateway;
  return { gateway, queries };
}

/** The workspace/export stubs: this page never compiles, only adds to a draft. */
const repository = { load: () => [], save: () => {} };
const exportGateway = { jobs: async () => [] } as never;

function renderPage(gateway: CatalogGateway, initialEntry = "/papers") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PreferencesProvider persist={false}>
        <ToastProvider>
          <AppServicesProvider
            services={{ gateway, draftRepository: repository, exportGateway }}
          >
            <CompositionWorkspaceProvider repository={repository} exportGateway={exportGateway}>
              <MemoryRouter initialEntries={[initialEntry]}>
                <PaperCatalogPageRoute />
              </MemoryRouter>
            </CompositionWorkspaceProvider>
          </AppServicesProvider>
        </ToastProvider>
      </PreferencesProvider>
    </QueryClientProvider>,
  );
}

describe("PaperCatalogPageRoute", () => {
  it("adds every row on the page in one action", async () => {
    const user = userEvent.setup();
    const { gateway } = gatewayWith([paper(1), paper(2), paper(3)]);
    renderPage(gateway);

    await screen.findByText(/示例系列 第 1 套/);
    // The bulk bar reports how many are on the page and adds them together.
    await user.click(screen.getByLabelText(/选择本页全部/));

    expect(await screen.findByText(/已加入本页 3 套/)).toBeInTheDocument();
    // Once selected, the header offers to remove them again.
    expect(screen.getByText(/移除本页已选（3）/)).toBeInTheDocument();
  });

  it("toggles a single row on and off, and counts it once", async () => {
    const user = userEvent.setup();
    const { gateway } = gatewayWith([paper(1), paper(2)]);
    renderPage(gateway);

    await screen.findByText(/示例系列 第 1 套/);
    const box = screen.getByLabelText("选择 2024/math1/demo/1");
    await user.click(box);
    expect(box).toBeChecked();
    // The bulk-bar count must reflect a single selection, not the page size.
    expect(await screen.findByText(/移除本页已选（1）/)).toBeInTheDocument();

    await user.click(box);
    expect(box).not.toBeChecked();
    await waitFor(() => expect(screen.queryByText(/移除本页已选/)).not.toBeInTheDocument());
  });

  it("sends the search text to the server instead of filtering the page", async () => {
    const user = userEvent.setup();
    const { gateway, queries } = gatewayWith([paper(1), paper(2), paper(3)]);
    renderPage(gateway);

    await screen.findByText(/示例系列 第 1 套/);
    queries.length = 0;
    await user.type(screen.getByLabelText("搜索"), "demo{Enter}");

    await waitFor(() => expect(queries.length).toBeGreaterThan(0), { timeout: 2000 });
    expect(queries.at(-1)?.query).toBe("demo");
  });

  it("reads the ordering from the URL and sends it to the server", async () => {
    const { gateway, queries } = gatewayWith([paper(1)]);
    renderPage(gateway, "/papers?order=year-desc");

    await screen.findByText(/示例系列 第 1 套/);
    await waitFor(() => expect(queries.length).toBeGreaterThan(0));
    expect(queries.at(-1)?.order).toBe("year-desc");
  });
});
