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
