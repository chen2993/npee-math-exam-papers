export type Subject = "math1" | "math2" | "math3";
type Section = "choice" | "fill" | "solution";

/** 一个图形：内嵌绘图或已批准的资源文件。 */
export interface Figure {
  kind: "tikz" | "asset";
  latex: string | null;
  path: string | null;
  description: string;
  exception_reason?: string | null;
}

/** 一段可选带图的文本块，用于题干、选项与子问。 */
interface Block {
  text: string;
  figures?: Figure[];
}

interface Choice {
  label: string;
  text: string;
  figures?: Figure[];
}

/** schema 3.0 题目。 */
export interface Question {
  number: number;
  section: Section;
  points: number | null;
  stem: Block;
  choices?: Choice[];
  subparts?: Block[];
}

/** 列表视图的套卷摘要，不含题目正文。 */
export interface PaperSummary {
  natural_key: string;
  bundle: string;
  series_key: string;
  series_name: string;
  year: number;
  subject: Subject;
  paper_no: number;
  question_count: number;
  section_counts: Record<string, number>;
  figure_count?: number;
  content_hash: string;
}

/**
 * 一套卷的规范文档，与写入接口接受的形状**完全一致**。
 *
 * 文档键（schema_version / paper / questions）在顶层，派生字段单独放在 `meta`。
 * 因此去掉 `meta` 就是一份合法的写入载荷——前端无需维护自己的转换层，也不会
 * 出现「读出来的形状写不回去」。
 */
export interface PaperDocument {
  schema_version: string;
  paper: {
    series_key: string;
    year: number;
    subject: Subject;
    paper_no: number;
  };
  questions: Question[];
  /** 磁盘文件内的自校验哈希；缺省表示来自旧文档。 */
  content_hash?: string;
  /** 由服务端派生，只读。 */
  meta: PaperSummary;
}

export interface Series {
  series_key: string;
  series_name: string;
  paper_count: number;
  question_count: number;
  years: number[];
  subjects: Subject[];
}

export interface Bundle {
  bundle: string;
  series_key: string;
  series_name: string;
  year: number;
  subject: Subject;
  paper_count: number;
}

interface LibraryStats {
  bundles: number;
  papers: number;
  questions: number;
  figures: number;
  series: string[];
  years: number[];
  subjects: Subject[];
  series_names?: Record<string, string>;
}

export interface Overview {
  stats: LibraryStats;
  series: Series[];
  bundles: Bundle[];
}

export interface PaperPage {
  total: number;
  offset: number;
  count: number;
  papers: PaperSummary[];
}

/** 一次调用记录的请求体或响应体。 */
export interface EventPayload {
  /** 解析后的 JSON（前端折叠展示）。 */
  json?: unknown;
  /** 非 JSON 文本原文。 */
  text?: string;
  /** 原始字节数。 */
  bytes?: number;
  /** 二进制内容只记大小与类型，不记内容。 */
  binary?: boolean;
  content_type?: string;
}

/** 一条操作事件：HTTP 请求或 MCP 工具调用。 */
export interface LogEvent {
  ts: string;
  surface: "http" | "mcp" | string;
  kind: "request" | "tool" | string;
  name: string;
  status: "ok" | "error" | string;
  /** HTTP 状态码；MCP 事件为 null。 */
  status_code: number | null;
  duration_ms: number | null;
  detail: Record<string, unknown>;
  request: EventPayload;
  response: EventPayload;
}

interface LogStats {
  path: string;
  events: number;
  bytes: number;
  max_bytes: number;
}

export interface LogPage {
  stats: LogStats;
  count: number;
  events: LogEvent[];
}

export interface LogQuery {
  limit?: number;
  surface?: string;
  kind?: string;
  status?: string;
  q?: string;
}

export interface ReleaseManifest {
  schema_version: string;
  library_hash: string;
  paper_count: number;
  papers: Record<string, string>;
}

/** 一次后台编译任务的快照。 */
export interface CompileJob {
  job_id: string;
  composition_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  artifacts: string[];
  error: string | null;
  report: Record<string, unknown>;
}

export const subjectNames: Record<Subject, string> = {
  math1: "数学一",
  math2: "数学二",
  math3: "数学三",
};

export const sectionNames: Record<Section, string> = {
  choice: "选择题",
  fill: "填空题",
  solution: "解答题",
};
