/**
 * Level three of the reader: one paper's questions.
 *
 * A single wide column, because a question set is read top to bottom (unlike a
 * table, where several columns are compared). Two aids are pinned to the top:
 * a section jump (选择题 / 填空题 / 解答题) and a 1..N question grid. The grid is
 * what makes "查看这一套的 22 题" navigable rather than a long scroll — the
 * current question is highlighted as the page moves.
 */

import { ChevronUp, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import type { CatalogGateway } from "../../application/catalog/ports";
import { usePaperDetail } from "../../application/query/hooks";
import type { PaperDocument, PaperSummary, Question, Section } from "../../domain/catalog/models";
import { sectionNames } from "../../domain/catalog/models";
import { QuestionView } from "../../shared/question/QuestionView";
import { IconButton, classNames } from "../../shared/ui";

const SECTION_ORDER: Section[] = ["choice", "fill", "solution"];

/**
 * Which question is currently at the top of the viewport.
 *
 * Uses one IntersectionObserver over every card and reports the *lowest*
 * question number among the visible ones. That is the question the reader is
 * looking at; a scroll-position calculation would have to re-measure on every
 * scroll event and would fight with lazy-loaded figures.
 */
function useActiveQuestion(numbers: number[], enabled: boolean) {
  const [active, setActive] = useState<number | null>(numbers[0] ?? null);
  const visible = useRef<Set<number>>(new Set());

  useEffect(() => {
    visible.current = new Set();
    setActive(numbers[0] ?? null);
    if (!enabled || !numbers.length) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const number = Number((entry.target as HTMLElement).dataset.questionNo);
          if (Number.isNaN(number)) continue;
          if (entry.isIntersecting) visible.current.add(number);
          else visible.current.delete(number);
        }
        if (visible.current.size) setActive(Math.min(...visible.current));
      },
      // The top inset clears the sticky jump bar; the bottom one keeps the
      // "current" question from flickering to whatever is entering the fold.
      { rootMargin: "-104px 0px -55% 0px", threshold: 0 },
    );

    const cards = document.querySelectorAll<HTMLElement>("[data-question-no]");
    cards.forEach((card) => observer.observe(card));
    return () => observer.disconnect();
  }, [numbers, enabled]);

  return active;
}

function scrollToQuestion(number: number) {
  document.querySelector<HTMLElement>(`[data-question-no="${number}"]`)?.scrollIntoView({ block: "start", behavior: "smooth" });
}

export function PaperReader({
  paper,
  gateway,
}: {
  paper: PaperSummary;
  gateway: CatalogGateway;
}) {
  const query = usePaperDetail(gateway, {
    seriesKey: paper.series_key,
    year: paper.year,
    subject: paper.subject,
    paperNo: paper.paper_no,
  });
  const detail = query.data as PaperDocument | undefined;
  const questions: Question[] = detail?.questions ?? [];
  const numbers = useMemo(() => questions.map((question) => question.number), [questions]);
  const active = useActiveQuestion(numbers, Boolean(questions.length));

  const sections = useMemo(() => {
    const bySection = new Map<Section, number[]>();
    for (const question of questions) {
      const list = bySection.get(question.section) ?? [];
      list.push(question.number);
      bySection.set(question.section, list);
    }
    return SECTION_ORDER.filter((section) => bySection.has(section)).map((section) => ({
      section,
      numbers: bySection.get(section)!,
    }));
  }, [questions]);

  if (query.isLoading) {
    return (
      <div className="reader-state">
        <LoaderCircle className="is-spinning" size={20} />正在读取题目
      </div>
    );
  }
  if (query.isError) {
    return (
      <div className="reader-state is-error">
        {query.error instanceof Error ? query.error.message : "读取题目失败"}
      </div>
    );
  }
  if (!detail) return null;

  return (
    <div className="reader-paper">
      <div className="reader-jump" role="navigation" aria-label="题目导航">
        <div className="reader-jump-sections">
          {sections.map(({ section, numbers: sectionNumbers }) => (
            <button
              key={section}
              type="button"
              className="reader-jump-section"
              onClick={() => scrollToQuestion(sectionNumbers[0])}
            >
              {sectionNames[section]}
              <span>{sectionNumbers.length}</span>
            </button>
          ))}
        </div>
        <div className="reader-jump-numbers">
          {numbers.map((number) => (
            <button
              key={number}
              type="button"
              className={classNames("reader-jump-number", number === active && "is-active")}
              aria-current={number === active ? "true" : undefined}
              onClick={() => scrollToQuestion(number)}
            >
              {number}
            </button>
          ))}
        </div>
        <IconButton label="回到顶部" size="sm" onClick={() => scrollToQuestion(numbers[0] ?? 1)}>
          <ChevronUp size={15} />
        </IconButton>
      </div>

      <div className="reader-questions">
        {questions.map((question) => (
          <div key={question.number} data-question-no={question.number} className="reader-question">
            <QuestionView question={question} paper={paper} />
          </div>
        ))}
      </div>
    </div>
  );
}
