import { BookOpenText, Check, LoaderCircle, Plus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { CatalogGateway } from "../../application/catalog/ports";
import { usePaperDetail } from "../../application/query/hooks";
import type { Figure, PaperDocument, PaperSummary, Question } from "../../domain/catalog/models";
import { sectionNames, subjectNames } from "../../domain/catalog/models";
import { useWorkspace } from "../../app/CompositionWorkspace";
import { Tex } from "../../shared/tex/Tex";
import { Button, IconButton } from "../../shared/ui";

/**
 * 渲染一个图形。
 *
 * TikZ 绘图由服务端编译为 SVG 后以图片展示，因此显示的是真实图形，而不是 KaTeX
 * 无法完成的近似。资源类图形直接加载。渲染失败的图形退化为占位说明，不会拖垮整页。
 */
function FigureView({
  figure,
  paper,
  questionNo,
  figureIndex,
}: {
  figure: Figure;
  paper: PaperSummary;
  questionNo: number;
  figureIndex: number;
}) {
  const [failed, setFailed] = useState(false);
  if (figure.kind === "asset" && figure.path) {
    return (
      <figure className="figure-block">
        <img src={`/api/assets/${figure.path}`} alt={figure.description} loading="lazy" />
        <figcaption>{figure.description}</figcaption>
      </figure>
    );
  }
  const source = `/api/figures/preview?series_key=${paper.series_key}&year=${paper.year}&subject=${paper.subject}&paper_no=${paper.paper_no}&question_no=${questionNo}&figure_index=${figureIndex}`;
  if (!failed) {
    return (
      <figure className="figure-block">
        <img src={source} alt={figure.description || "图形"} loading="lazy" onError={() => setFailed(true)} />
        {figure.description ? <figcaption>{figure.description}</figcaption> : null}
      </figure>
    );
  }
  const firstLine = (figure.latex || "").trim().split("\n")[0].slice(0, 60);
  return (
    <figure className="figure-block figure-placeholder">
      <div className="figure-placeholder-body">
        <span className="eyebrow">TIKZ</span>
        <code>
          {firstLine}
          {firstLine.length >= 60 ? "…" : ""}
        </code>
      </div>
      <figcaption>{figure.description || "图形（无法渲染，请检查 XeLaTeX 环境）"}</figcaption>
    </figure>
  );
}

function ChoiceView({
  label,
  text,
  figures,
  paper,
  questionNo,
  figureOffset,
}: {
  label: string;
  text: string;
  figures?: Figure[];
  paper: PaperSummary;
  questionNo: number;
  figureOffset: number;
}) {
  return (
    <div className="question-choice">
      <span className="choice-label">{label}</span>
      <div className="choice-body">
        {text ? <Tex source={text} /> : null}
        {figures?.map((figure, index) => (
          <FigureView key={index} figure={figure} paper={paper} questionNo={questionNo} figureIndex={figureOffset + index} />
        ))}
      </div>
    </div>
  );
}

export function QuestionView({ question, paper }: { question: Question; paper: PaperSummary }) {
  // 图形按题干、选项、子问顺序统一编号，使预览接口无需了解题目内部结构即可定位。
  const stemFigures = question.stem.figures || [];
  let offset = stemFigures.length;
  const choiceOffsets = (question.choices || []).map((choice) => {
    const current = offset;
    offset += (choice.figures || []).length;
    return current;
  });
  const subpartOffsets = (question.subparts || []).map((subpart) => {
    const current = offset;
    offset += (subpart.figures || []).length;
    return current;
  });

  return (
    <article className="question-card">
      <header className="question-card-head">
        <span className="question-number">{question.number}</span>
        <span className="question-section">{sectionNames[question.section]}</span>
        {question.points !== null && <span className="question-points">{question.points} 分</span>}
      </header>
      <div className="question-stem">
        <Tex source={question.stem.text} />
        {stemFigures.map((figure, index) => (
          <FigureView key={index} figure={figure} paper={paper} questionNo={question.number} figureIndex={index} />
        ))}
      </div>
      {question.choices?.length ? (
        <div className="question-choices">
          {question.choices.map((choice, index) => (
            <ChoiceView
              key={choice.label}
              label={choice.label}
              text={choice.text}
              figures={choice.figures}
              paper={paper}
              questionNo={question.number}
              figureOffset={choiceOffsets[index]}
            />
          ))}
        </div>
      ) : null}
      {question.subparts?.length ? (
        <ol className="question-subparts">
          {question.subparts.map((subpart, index) => (
            <li key={index}>
              <Tex source={subpart.text} />
              {(subpart.figures || []).map((figure, figureIndex) => (
                <FigureView
                  key={figureIndex}
                  figure={figure}
                  paper={paper}
                  questionNo={question.number}
                  figureIndex={subpartOffsets[index] + figureIndex}
                />
              ))}
            </li>
          ))}
        </ol>
      ) : null}
    </article>
  );
}

export function PaperDetailDrawer({
  paper,
  gateway,
  onClose,
}: {
  paper: PaperSummary;
  gateway: CatalogGateway;
  onClose: () => void;
}) {
  const workspace = useWorkspace();
  // One query per paper; the cache makes reopening the same paper instant.
  const query = usePaperDetail(gateway, {
    seriesKey: paper.series_key,
    year: paper.year,
    subject: paper.subject,
    paperNo: paper.paper_no,
  });
  const detail = query.data as PaperDocument | undefined;
  const loading = query.isLoading;
  const error = query.isError ? (query.error instanceof Error ? query.error.message : "读取题目失败") : "";
  // The passed summary can be a placeholder (a deep link from a search hit knows
  // the natural key but not the display name); the fetched document always
  // carries the real one in `meta`, so prefer it for the header once it arrives.
  const shown = detail?.meta ?? paper;
  const selected = workspace.isSelected(paper.natural_key);
  const bodyRef = useRef<HTMLDivElement>(null);

  // Escape closes the drawer and the background must not scroll underneath it —
  // both are expected of a panel that covers the page, and their absence is felt
  // most on a long paper.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    bodyRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose]);

  return (
    <div className="drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`${shown.series_name} 第 ${shown.paper_no} 套`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <span className="eyebrow">{subjectNames[shown.subject]} · {shown.year}</span>
            <h3>
              {shown.series_name} 第 {shown.paper_no} 套
            </h3>
          </div>
          <Button
            size="sm"
            variant={selected ? "primary" : "default"}
            icon={selected ? <Check size={14} /> : <Plus size={14} />}
            onClick={() => workspace.togglePaper(shown)}
          >
            {selected ? "已加入" : "加入组卷"}
          </Button>
          <IconButton label="关闭" onClick={onClose}>
            <X size={17} />
          </IconButton>
        </header>
        {/* Focusable so the Escape handler and the scroll container both work. */}
        <div className="drawer-body" ref={bodyRef} tabIndex={-1}>
          {loading && (
            <div className="drawer-state">
              <LoaderCircle className="is-spinning" size={20} />正在读取题目
            </div>
          )}
          {error && <div className="drawer-state drawer-error">{error}</div>}
          {detail && !loading && (
            <>
              <div className="drawer-summary">
                <BookOpenText size={15} />
                共 {detail.meta.question_count} 题
                {detail.meta.figure_count ? ` · ${detail.meta.figure_count} 图` : ""}
              </div>
              {detail.questions.map((question) => (
                <QuestionView key={question.number} question={question} paper={paper} />
              ))}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
