import type { PaperSummary, Subject } from "../catalog/models";

/**
 * A self-contained reference to one selected paper.
 *
 * Storing the display fields alongside the natural key means a draft can be
 * rendered, exported and compiled **without** the paper being present on the
 * page the user happens to be looking at. The previous design stored bare natural
 * keys and resolved them against the currently loaded page, which is why the UI
 * had to warn about "已选但不在当前页" papers.
 */
export interface PaperRef {
  series_key: string;
  year: number;
  subject: Subject;
  paper_no: number;
  /** Display name captured at selection time. */
  series_name: string;
  /** Question count captured at selection time (display only). */
  question_count: number;
  /** Natural key, kept for stable React keys and de-duplication. */
  natural_key: string;
}

export function paperRefFromSummary(paper: PaperSummary): PaperRef {
  return {
    series_key: paper.series_key,
    year: paper.year,
    subject: paper.subject,
    paper_no: paper.paper_no,
    series_name: paper.series_name,
    question_count: paper.question_count,
    natural_key: paper.natural_key,
  };
}

/** Rebuild a display summary from a stored reference. */
export function paperSummaryFromRef(ref: PaperRef): PaperSummary {
  return {
    natural_key: ref.natural_key,
    bundle: `${ref.series_key}-${ref.year}-${ref.subject}`,
    series_key: ref.series_key,
    series_name: ref.series_name,
    year: ref.year,
    subject: ref.subject,
    paper_no: ref.paper_no,
    question_count: ref.question_count,
    section_counts: {},
    content_hash: "",
  };
}

export type Layout = "a3" | "a4" | "both";
export type Theme = "print" | "cream" | "both";
export type Spacing = "compact" | "spaced" | "a4-blank" | "both";
export type SolutionStructure = "pair-first" | "natural" | "full-page";

export interface OpeningSettings {
  show: boolean;
  candidateInfo: boolean;
  notices: boolean;
}
export interface WatermarkSettings {
  enabled: boolean;
  text: string;
  color: string;
  opacity: number;
  textColor: string;
  backgroundColor: string;
}

export interface CompositionDraft {
  id: string;
  name: string;
  /** Ordered selection; the array order is the print order. */
  papers: PaperRef[];
  createdAt: string;
  layout: Layout;
  theme: Theme;
  spacing: Spacing;
  structure: SolutionStructure;
  pairCount: number;
  toc: boolean;
  allSubjects: boolean;
  opening: OpeningSettings;
  watermark: WatermarkSettings;
}

export interface CompositionDownload {
  blob: Blob;
  filename: string;
  format: "pdf" | "zip";
}

export function createDraft(name = "新组卷"): CompositionDraft {
  return {
    id: `composition-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    name,
    papers: [],
    createdAt: new Date().toISOString(),
    layout: "both",
    theme: "print",
    spacing: "spaced",
    structure: "pair-first",
    pairCount: 2,
    toc: true,
    allSubjects: false,
    opening: { show: true, candidateInfo: true, notices: true },
    watermark: {
      enabled: false,
      text: "",
      color: "rgba(20, 80, 70, 0.35)",
      opacity: 0.35,
      textColor: "rgba(20, 80, 70, 0.9)",
      backgroundColor: "rgba(255, 255, 255, 0.18)",
    },
  };
}

export function normalizeSpacing(value: unknown): CompositionDraft["spacing"] {
  return value === "compact" || value === "spaced" || value === "a4-blank" || value === "both" ? value : "spaced";
}

function outputTargets(draft: CompositionDraft) {
  const layouts = draft.spacing === "a4-blank" ? (["a4"] as const) : draft.layout === "both" ? (["a3", "a4"] as const) : [draft.layout];
  const themes = draft.theme === "both" ? (["print", "cream"] as const) : [draft.theme];
  const spacings = draft.spacing === "both" ? (["compact", "spaced"] as const) : [draft.spacing];
  return layouts.flatMap((layout) =>
    themes.flatMap((theme) => spacings.map((spacing) => ({ layout, theme, spacing, enabled: true, answers: false, output_suffix: null }))),
  );
}

/**
 * How many PDF files a draft will produce.
 *
 * Each layout × theme × spacing combination is one file, so `页面=both` plus
 * `纸色=both` plus `间距=both` silently multiplies out to 8. The compose page
 * shows this count next to the compile button: a long typeset run is worth
 * understanding before it starts.
 */
export function outputTargetCount(draft: CompositionDraft): number {
  return outputTargets(draft).length;
}

/**
 * 生成应用 API 的编译请求载荷。
 *
 * 载荷只携带 series/year/subject/paper_no 选择；后端会推导并封印每套卷的
 * ``content_hash``，因此前端无需了解哈希，也不可能封印一个过期值。
 */
/**
 * Generate the application API's compile payload.
 *
 * The payload carries only series/year/subject/paper_no selections; the backend
 * derives and pins each paper's ``content_hash``, so the frontend never needs to
 * know the hash and can never pin a stale one.
 *
 * ``papers`` defaults to the draft's own stored references, which is what makes
 * export work even when the selected papers are not on the current page.
 */
export function buildCompilePayload(draft: CompositionDraft, papers?: PaperSummary[]) {
  const selections = (papers ?? draft.papers.map(paperSummaryFromRef)).map((paper) => ({
    series_key: paper.series_key,
    year: paper.year,
    subject: paper.subject,
    paper_no: paper.paper_no,
  }));
  const document = {
    toc: { enabled: draft.toc, title: "目录", include_groups: true, include_papers: true },
    layout: draft.layout,
    theme: draft.theme,
    spacing: draft.spacing,
    opening: { show: draft.opening.show, candidate_info: draft.opening.candidateInfo, notices: draft.opening.notices },
    solution: { structure: draft.structure, pair_count: draft.pairCount },
    watermark: {
      enabled: draft.watermark.enabled,
      text: draft.watermark.text,
      color: draft.watermark.color,
      opacity: draft.watermark.opacity,
      text_color: draft.watermark.textColor,
      background_color: draft.watermark.backgroundColor,
    },
  };
  return {
    // The backend only accepts lowercase ids matching ^[a-z0-9][a-z0-9-]*$,
    // so normalise any user- or storage-derived id here rather than failing at
    // the API boundary.
    composition_id: draft.id
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^[^a-z0-9]+/, "")
      .slice(0, 120) || "composition",
    title: draft.name || "未命名组卷",
    selections,
    document,
    compile: {
      engine: "xelatex",
      passes: 3,
      targets: outputTargets(draft),
      output: {
        directory: "build/output",
        filename_template: "[{layout}][{subject_label}][{spacing_label}] {title}.pdf",
        overwrite: true,
      },
    },
  };
}

export function subjectLabel(subject: Subject): string {
  return { math1: "数学一", math2: "数学二", math3: "数学三" }[subject];
}

/**
 * Rebuild a draft from an exported compile payload.
 *
 * This is the exact inverse of {@link buildCompilePayload}: export writes the
 * payload, import reads it back, so the two stay in step. Display fields the
 * payload does not carry (series_name, question_count) fall back to the
 * natural-key parts; the paper list backfills them once the catalogue loads.
 * Unknown or missing values fall back to {@link createDraft}'s defaults rather
 * than throwing, because a hand-edited export should degrade, not fail.
 */
export function draftFromCompilePayload(payload: unknown): CompositionDraft {
  if (!payload || typeof payload !== "object") throw new Error("不是合法的组卷 JSON");
  const raw = payload as Record<string, unknown>;
  const selections = Array.isArray(raw.selections) ? raw.selections : [];
  if (!selections.length) throw new Error("组卷 JSON 里没有 selections");

  const papers: PaperRef[] = [];
  for (const entry of selections) {
    if (!entry || typeof entry !== "object") throw new Error("selections 里存在非对象条目");
    const item = entry as Record<string, unknown>;
    const series_key = String(item.series_key ?? "");
    const subject = String(item.subject ?? "") as Subject;
    const year = Number(item.year);
    const paper_no = Number(item.paper_no);
    if (!series_key || !year || !paper_no || !["math1", "math2", "math3"].includes(subject)) {
      throw new Error(`selections 条目缺少必要的 series_key/year/subject/paper_no：${JSON.stringify(entry)}`);
    }
    papers.push({
      series_key,
      year,
      subject,
      paper_no,
      series_name: series_key,
      question_count: 0,
      natural_key: `${year}/${subject}/${series_key}/${paper_no}`,
    });
  }

  const document = (raw.document ?? {}) as Record<string, unknown>;
  const toc = (document.toc ?? {}) as Record<string, unknown>;
  const opening = (document.opening ?? {}) as Record<string, unknown>;
  const solution = (document.solution ?? {}) as Record<string, unknown>;
  const watermark = (document.watermark ?? {}) as Record<string, unknown>;
  const defaults = createDraft();

  return {
    ...defaults,
    name: typeof raw.title === "string" && raw.title.trim() ? raw.title : defaults.name,
    papers,
    layout: normalizeLayout(document.layout),
    theme: normalizeTheme(document.theme),
    spacing: normalizeSpacing(document.spacing),
    structure: normalizeStructure(solution.structure),
    pairCount:
      typeof solution.pair_count === "number" ? Math.min(8, Math.max(1, solution.pair_count)) : defaults.pairCount,
    toc: typeof toc.enabled === "boolean" ? toc.enabled : defaults.toc,
    opening: {
      show: typeof opening.show === "boolean" ? opening.show : defaults.opening.show,
      candidateInfo:
        typeof opening.candidate_info === "boolean" ? opening.candidate_info : defaults.opening.candidateInfo,
      notices: typeof opening.notices === "boolean" ? opening.notices : defaults.opening.notices,
    },
    watermark: {
      ...defaults.watermark,
      enabled: typeof watermark.enabled === "boolean" ? watermark.enabled : defaults.watermark.enabled,
      text: typeof watermark.text === "string" ? watermark.text : defaults.watermark.text,
      color: typeof watermark.color === "string" ? watermark.color : defaults.watermark.color,
      opacity: typeof watermark.opacity === "number" ? watermark.opacity : defaults.watermark.opacity,
      textColor: typeof watermark.text_color === "string" ? watermark.text_color : defaults.watermark.textColor,
      backgroundColor:
        typeof watermark.background_color === "string" ? watermark.background_color : defaults.watermark.backgroundColor,
    },
  };
}

function normalizeLayout(value: unknown): Layout {
  return value === "a3" || value === "a4" || value === "both" ? value : "both";
}

function normalizeTheme(value: unknown): Theme {
  return value === "print" || value === "cream" || value === "both" ? value : "print";
}

function normalizeStructure(value: unknown): SolutionStructure {
  return value === "pair-first" || value === "natural" || value === "full-page" ? value : "pair-first";
}
