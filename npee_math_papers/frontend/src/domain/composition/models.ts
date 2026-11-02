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
/**
 * 间距：只决定**解答题**怎么排。
 *
 * `compact` 自然连排；`spaced` 让解答题独占页面（17–18 共用一页，之后每题一页），
 * 给作答留出书写空间。留白是另一个独立开关（{@link CompositionDraft.printBlank}），
 * 与间距互不影响。
 */
export type Spacing = "compact" | "spaced" | "both";

/**
 * 新草稿可选的间距：紧凑（自然连排）与宽松（解答题独占页面）。
 */
const PRODUCT_SPACINGS = ["compact", "spaced"] as const;

interface OpeningSettings {
  show: boolean;
  candidateInfo: boolean;
  notices: boolean;
}
interface WatermarkSettings {
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
  /** 留白：每套卷补足整页、封面后加空白页、目录凑偶数页（与间距无关）。 */
  printBlank: boolean;
  toc: boolean;
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
    spacing: "compact",
    printBlank: true,
    toc: true,
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
  // 旧草稿把「紧凑 + 留白」写成一个值（`print` / `a4-blank`）；间距本身只认
  // compact / spaced，留白由 normalizePrintBlank 单独读出来。
  if (value === "print" || value === "a4-blank") return "compact";
  return value === "compact" || value === "spaced" || value === "both" ? value : "compact";
}

/**
 * 留白开关的归一化。
 *
 * 新数据直接读 ``printBlank``；旧草稿只写了 ``spacing: "print" | "a4-blank"``，
 * 那时它同时表达了留白，因此这里把它折算成"打开留白"。
 */
export function normalizePrintBlank(value: unknown, legacySpacing: unknown): boolean {
  if (typeof value === "boolean") return value;
  if (legacySpacing === "print" || legacySpacing === "a4-blank") return true;
  // 载荷里完全没有留白信息时，跟随新草稿的默认值（留白开启）。
  return createDraft().printBlank;
}

function outputTargets(draft: CompositionDraft) {
  // The print deliverable is layout-agnostic, so the chosen stocks are used as
  // they stand; no spacing forces a particular paper size.
  const layouts = draft.layout === "both" ? (["a3", "a4"] as const) : [draft.layout];
  const themes = draft.theme === "both" ? (["print", "cream"] as const) : [draft.theme];
  const spacings = draft.spacing === "both" ? PRODUCT_SPACINGS : [draft.spacing];
  return layouts.flatMap((layout) =>
    themes.flatMap((theme) =>
      spacings.map((spacing) => ({
        layout,
        theme,
        spacing,
        print: draft.printBlank,
        enabled: true,
        answers: false,
        output_suffix: null,
      })),
    ),
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
  const watermark = (document.watermark ?? {}) as Record<string, unknown>;
  const defaults = createDraft();
  // 旧载荷把间距与留白合在一起（spacing=print/a4-blank），新载荷分两个字段。
  const compileConfig = (raw.compile ?? {}) as Record<string, unknown>;
  const targets = Array.isArray(compileConfig.targets) ? compileConfig.targets : [];
  const firstTarget = (targets.find((item) => item && typeof item === "object") ?? {}) as Record<string, unknown>;
  const enabledTargets = targets.filter(
    (item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && item.enabled !== false,
  );
  const blankSet = new Set(enabledTargets.map((item) => item.print === true));
  const spacingSet = new Set(
    enabledTargets.map((item) => normalizeSpacing(item.spacing)).filter((value) => value !== "both"),
  );
  const layoutSet = new Set(
    enabledTargets.map((item) => normalizeLayout(item.layout)).filter((value) => value !== "both"),
  );
  const themeSet = new Set(
    enabledTargets.map((item) => normalizeTheme(item.theme)).filter((value) => value !== "both"),
  );

  return {
    ...defaults,
    name: typeof raw.title === "string" && raw.title.trim() ? raw.title : defaults.name,
    papers,
    layout: enabledTargets.length ? (layoutSet.size === 1 ? ([...layoutSet][0] as Layout) : "both") : normalizeLayout(document.layout),
    theme: enabledTargets.length ? (themeSet.size === 1 ? ([...themeSet][0] as Theme) : "both") : normalizeTheme(document.theme),
    spacing: enabledTargets.length ? (spacingSet.size === 1 ? ([...spacingSet][0] as CompositionDraft["spacing"]) : "both") : normalizeSpacing(document.spacing),
    // 留白优先读 document.print，其次读目标矩阵（新载荷把开关写在每个 target 上），
    // 都没有才回落到旧的组合写法（spacing=print/a4-blank）。
    // 与 layout/theme/spacing 同理：目标矩阵才是事实源，文档头只是生成时的意向。
    printBlank: enabledTargets.length
      ? blankSet.has(true)
      : normalizePrintBlank(
          document.print !== undefined ? document.print : firstTarget.print,
          document.spacing,
        ),
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

/**
 * 把服务端的组卷包文档读成一份可编辑草稿。
 *
 * 组卷包里的引用可能是 ``subject: "$subject"`` 的三科模板（一套引用在每个科目下
 * 各排一次）。草稿是一维的套卷列表，所以这里按 ``compile.subjects`` 展开成具体
 * 套卷——展开后的列表与实际会排版出来的卷数一致。
 */
export function draftFromCompositionDocument(
  composition: Record<string, unknown>,
  fallbackName = "组卷",
): CompositionDraft {
  const compile = (composition.compile ?? {}) as Record<string, unknown>;
  const document = (composition.document ?? {}) as Record<string, unknown>;
  const groups = Array.isArray(composition.groups) ? composition.groups : [];
  const subjects = Array.isArray(compile.subjects) && compile.subjects.length
    ? (compile.subjects as string[])
    : ["math1"];
  const metadata = (composition.metadata ?? {}) as Record<string, unknown>;

  const papers: PaperRef[] = [];
  const seen = new Set<string>();
  for (const group of groups) {
    const entries = (group as Record<string, unknown>).papers;
    if (!Array.isArray(entries)) continue;
    for (const entry of entries) {
      if (!entry || typeof entry !== "object") continue;
      const item = entry as Record<string, unknown>;
      const year = Number(item.year);
      const paperNo = Number(item.paper_no);
      const seriesKey = String(item.series_key ?? "");
      if (!seriesKey || !year || !paperNo) continue;
      const rawSubject = String(item.subject ?? "");
      const targets = rawSubject === "$subject" ? subjects : [rawSubject];
      for (const subject of targets) {
        if (!["math1", "math2", "math3"].includes(subject)) continue;
        const naturalKey = `${year}/${subject}/${seriesKey}/${paperNo}`;
        if (seen.has(naturalKey)) continue;
        seen.add(naturalKey);
        papers.push({
          series_key: seriesKey,
          year,
          subject: subject as Subject,
          paper_no: paperNo,
          series_name: String(item.display_title ?? item.bookmark_title ?? seriesKey),
          question_count: 0,
          natural_key: naturalKey,
        });
      }
    }
  }

  const defaults = createDraft();
  const opening = (document.opening ?? {}) as Record<string, unknown>;
  const toc = (document.toc ?? {}) as Record<string, unknown>;
  const watermark = (document.watermark ?? {}) as Record<string, unknown>;
  const targets = Array.isArray(compile.targets) ? compile.targets : [];
  const firstTarget = (targets.find((item) => item && typeof item === "object") ?? {}) as Record<string, unknown>;
  // 目标矩阵才是"真正会编译什么"的事实源：文档头里的 layout/theme/spacing 只是
  // 生成时的意向，正式组卷包里可能出现两者不一致（例如文档写 both、目标全是紧凑）。
  const enabledTargets = targets.filter(
    (item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && item.enabled !== false,
  );
  const spacingSet = new Set(
    enabledTargets.map((item) => normalizeSpacing(item.spacing)).filter((value) => value !== "both"),
  );
  const layoutSet = new Set(
    enabledTargets.map((item) => normalizeLayout(item.layout)).filter((value) => value !== "both"),
  );
  const themeSet = new Set(
    enabledTargets.map((item) => normalizeTheme(item.theme)).filter((value) => value !== "both"),
  );
  const spacing: CompositionDraft["spacing"] =
    spacingSet.size === 1 ? ([...spacingSet][0] as CompositionDraft["spacing"]) : "both";
  const layout: Layout = layoutSet.size === 1 ? ([...layoutSet][0] as Layout) : "both";
  const theme: Theme = themeSet.size === 1 ? ([...themeSet][0] as Theme) : "both";
  const blankSet = new Set(enabledTargets.map((item) => item.print === true));

  return {
    ...defaults,
    papers,
    name: String(metadata.title ?? composition.composition_id ?? fallbackName),
    layout: enabledTargets.length ? layout : normalizeLayout(document.layout),
    theme: enabledTargets.length ? theme : normalizeTheme(document.theme),
    spacing: enabledTargets.length ? spacing : normalizeSpacing(document.spacing),
    printBlank: normalizePrintBlank(
      document.print !== undefined ? document.print : firstTarget.print,
      document.spacing,
    ),
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
