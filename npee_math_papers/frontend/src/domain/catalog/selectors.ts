import type { PaperSummary, Series, Subject } from "./models";

export const subjectNames: Record<Subject, string> = {
  math1: "数学一",
  math2: "数学二",
  math3: "数学三",
};

/** 返回套卷的规范键。 */
export function paperKey(paper: Pick<PaperSummary, "natural_key">): string {
  return paper.natural_key;
}

/** 返回系列的显示名，找不到时回退为键本身。 */
export function seriesName(series: Series[], key: string): string {
  return series.find((item) => item.series_key === key)?.series_name || key;
}

export function findPaperByKey(papers: PaperSummary[], key: string): PaperSummary | undefined {
  return papers.find((paper) => paper.natural_key === key);
}

/** 以规范键建立 Map，实现 O(1) 查找。 */
export function indexPapers(papers: PaperSummary[]): Map<string, PaperSummary> {
  return new Map(papers.map((paper) => [paper.natural_key, paper]));
}

export function rangeLabel(offset: number, count: number, total: number): string {
  if (!total) return "0 套";
  return `${offset + 1}-${offset + count} / ${total} 套`;
}
