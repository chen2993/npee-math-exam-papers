/**
 * Shared question rendering: figure, choice and whole-question views.
 *
 * Extracted from the catalogue drawer because the standalone reader renders the
 * same trees. Keeping one implementation means a rendering fix (a new figure
 * kind, a numbering rule) cannot apply to only one of the two surfaces.
 */

import { useState } from "react";

import type { Figure, PaperSummary, Question } from "../../domain/catalog/models";
import { sectionNames } from "../../domain/catalog/models";
import { Tex } from "../tex/Tex";

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

