/**
 * Catalogue behaviour that is easy to regress and invisible to a type check:
 * the search box is sent to the *server* rather than filtering the loaded page,
 * ordering comes from the URL, a row opens the question drawer, and the page
 * carries no composition affordances at all.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { CatalogGateway, PaperQuery } from "../../application/catalog/ports";
import { AppServicesProvider } from "../../app/AppServices";
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

const repository = { load: () => [], save: () => {} };
const exportGateway = { jobs: async () => [] } as never;

function renderPage(gateway: CatalogGateway, initialEntry = "/papers") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PreferencesProvider persist={false}>
        <ToastProvider>
          <AppServicesProvider services={{ gateway, draftRepository: repository, exportGateway }}>
            <MemoryRouter initialEntries={[initialEntry]}>
              <PaperCatalogPageRoute />
            </MemoryRouter>
          </AppServicesProvider>
        </ToastProvider>
      </PreferencesProvider>
    </QueryClientProvider>,
  );
}

describe("PaperCatalogPageRoute", () => {
  it("lists the papers without any composition affordance", async () => {
    const { gateway } = gatewayWith([paper(1), paper(2)]);
    renderPage(gateway);

    await screen.findByText(/示例系列 第 1 套/);
    expect(screen.getByText(/示例系列 第 2 套/)).toBeInTheDocument();
    // Browsing must not depend on the composition workspace: no bulk-add, no
    // select-all, no "open the draft" entry point.
    expect(screen.queryByText(/加入组卷|打开组卷/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/选择本页全部/)).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("opens the question drawer from a row", async () => {
    const user = userEvent.setup();
    const { gateway } = gatewayWith([paper(1)]);
    (gateway.getPaper as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      schema_version: "3.0",
      paper: { series_key: "demo", year: 2024, subject: "math1", paper_no: 1 },
      meta: { ...paper(1), question_count: 0 },
      questions: [],
    });
    renderPage(gateway);

    await screen.findByText(/示例系列 第 1 套/);
    await user.click(screen.getByRole("button", { name: "查看题目" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(gateway.getPaper).toHaveBeenCalled();
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
