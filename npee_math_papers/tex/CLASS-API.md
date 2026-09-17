# `npee-math-exam` Class API

`npee_math_papers/tex/npee-math-exam.cls` is the reusable typesetting engine for Chinese
mathematics examinations. It owns layout, typography, counters, candidate
forms, question environments, page overlays, bookmarks, and answer-space flow.
It does not own a publication title, subject wording, publisher artwork,
question text, cover, back matter, or source metadata. Those belong to a project
or composition JSON and are injected by the generated `.tex`.

The class requires XeLaTeX or LuaLaTeX and is distributed separately from all
question and publisher material.

## Minimal document

```tex
\documentclass[a4,print,spaced]{npee-math-exam}

% Project metadata is optional. Define only what the project uses.
\renewcommand{\NPEESubjectCode}{301}
\ExamSetup{
  watermark/show=false,
  security/level=0
}

\begin{document}
  \ExamBeginBookBody
  \begin{ExamPaper}[bookmark-title={第1套},bookmark-key={paper-01}]
    \ExamSection{选择题}
    \begin{ExamChoiceQuestion}[id=q1,points=5]
      若 $f(x)=x^2$，则 $f'(1)$ 等于\ExamSelection。
      \ExamChoices{$0$}{$1$}{$2$}{$3$}
    \end{ExamChoiceQuestion}
  \end{ExamPaper}
\end{document}
```

The question source contains content only. The class creates question numbers,
section numbers, option labels, page footer, and (when enabled) the candidate
information opening page.

## Class options

| Option | Default | Meaning |
| --- | --- | --- |
| `a3` | `a3` | A3 landscape spread with two logical columns |
| `a4` | `a3` | A4 paper, one continuous text column per physical page |
| `print`, `white`, `normal` | `print` | White print palette |
| `eyecare`, `eye`, `cream` | `print` | Warm examination-paper palette |
| `spaced` | `spaced` | Structured solution pagination: 17--18 share logical page 4, then one solution question per logical page |
| `compact` | `spaced` | Natural flow for all sections, with the same body typography as `spaced` |
| `a4-blank` | `spaced` | Print deliverable: compact natural flow, every paper padded to at least four physical pages. Layout-agnostic — on A3 it matches `compact` |
| `inlineonly` | off | Diagnose display-math entry points |
| `candidateinfo` / `nocandidateinfo` | on | Candidate information form in the paper opening page |
| `candidatenotices` / `nocandidatenotices` | on | Notice block in the paper opening page |
| `opening` / `noopening` | on | Paper opening page containing the paper title |
| `watermark` / `nowatermark` | off | Exam-page watermark (also needs non-empty `watermark/text`) |
| `securitymark` / `nosecuritymark` | off | Opening security mark |
| `answers` / `noanswers` | off | Inline answer/solution visibility |
| `math1`, `math2`, `math3` | none | Compatibility selectors for old sources |

The paper opening page is independent from the optional composition cover. Its
title is always retained while the candidate form and notice block are controlled
separately. With both blocks disabled, the title is placed at the top of the first
paper column, so no empty opening page is created. Both overlays -- the exam-page
watermark and the opening security mark -- default to *off*; a publication that
wants either one opts in (see the `watermark`/`securitymark` options above). Cover, appendix, and back-matter pages should use their own
project styles and can turn off exam overlays through the lifecycle commands below.

## Global setup

```tex
\ExamSetup{
  body/font-size=12pt,
  body/line-height=18pt,
  section/font-size=13.5pt,
  section/line-height=18.5pt,
  column/gap=14mm,
  column/rule=0pt,
  spacing/mode=a4-blank,
  eyecare/paper-color={FFF9E2},
  eyecare/text-color={322D26},
  watermark/show=false,
  watermark/text={试卷库},
  watermark/angle=24,
  watermark/opacity=.12,
  watermark/font-size=24pt,
  security/level=3,   % 设置等级会同时显示密级标记
  security/text={内部资料},
  security/suffix={启用前},
  opening/show=true,
  candidate-info/show=true,
  candidate-notices/show=true,
  candidate-info/label-width=31.5mm,
  candidate-info/row-height=9.3mm,
  choices/indent=5mm,
  blank/width=17mm,
  paper/page-count=8,
  solution/structure=pair-first,
  solution/pair-count=2
}
```

Frequently used setters have neutral `Exam*` names:

```tex
\ExamSetQuestionPointsFormat{（本题满分}{分）}
\ExamSetQuestionPointsStyle{\textup}
\ExamSetPageCount{8}
\ExamUseAutomaticPageCount
```

答题区只由解题结构配置，题目源和组卷 JSON 不写物理高度。默认
`solution/structure=pair-first` 将首组两题放入同一答题单元，后续题目按版式
逐单元推进；`natural` 让题面自然流动，`full-page` 让每题占用一个完整答题单元。
`solution/pair-count` 可调整首组题数。答题单元的实际高度由 A3/A4 纸张和
`spaced`/`compact` 模式在类内部推导。

`a4-blank` 是组卷编译目标而不是普通题面间距：它强制使用 A4、采用紧凑自然流动，
并在每套试卷结束时补足到至少 4 页；已有 `compact` 和 `spaced` 目标不受影响。

历史题源中的显式答题高度只由类内部迁移层兼容，并会触发一次弃用警告；它们不是
公共 API，也不应出现在新的题库记录、组合 JSON 或生成的题面中。迁移时删除高度
参数，改用上述解答题结构即可。

Extensions can register `/npee_math_papers` keys with `\NPEEDeclareSetupKey`,
`\NPEEDeclareSetupKeys`, `\NPEEDeclareSetupStyle`, and
`\NPEEDeclareSetupIf`. The `NPEE*` names are implementation/compatibility
names; project sources should prefer the `Exam*` aliases documented here.

## Paper lifecycle and navigation

```tex
\ExamBeginBookBody
\begin{ExamPaper}[bookmark-title={第1套},bookmark-key={paper-01}]
  % sections and questions
\end{ExamPaper}

\ExamBeginAppendix{附录}{appendix}
\input{project/answer-card.tex}

\ExamBackMatterStart{末页}
\input{project/back-matter.tex}
```

For a manifest that imports body fragments, use a collection:

```tex
\begin{ExamCollection}
  \ExamCollectionContents
  \ExamCollectionSection[entry]{入门}
  \ExamInputPaper[bookmark-title={第1套},bookmark-key={paper-01}]{generated/paper-01}
  \ExamInputPaper[bookmark-title={第2套},bookmark-key={paper-02}]{generated/paper-02}
\end{ExamCollection}
```

`\ExamInputPaper` owns the start/input/end lifecycle and resets paper metadata.
`\ExamInputLegacyPaper` is only for old fragments that open and close their own
paper. `\ExamInputPaperList{a,b,c}` is a convenience form when default
bookmarks are sufficient. Group headings are inserted with
`\ExamCollectionSection[stable-key]{visible title}` and are never nested inside
an active paper.

## Candidate information and publication metadata

The class provides neutral defaults and allows a project to replace every
visible label and notice:

```tex
\renewcommand{\NPEESubjectCode}{301}
\renewcommand{\NPEECandidateNoticeHeading}{考生注意事项}
\renewcommand{\NPEECandidateInformationHeading}{（以下信息考生必须认真填写）}
\renewcommand{\NPEECandidateNumberLabel}{考生编号}
\renewcommand{\NPEECandidateNameLabel}{考生姓名}
\NPEESetCandidateNotices{...}
\NPEESetCandidateInfo{标题}{信息栏标题}{编号}{姓名}{通知内容}
```

Subject code rendering is provided by `\NPEEFormatSubjectCode{301}` and yields
`（科目代码：301）`. The class does not infer a subject name from the code.
Document metadata can be supplied with `\NPEESetDocumentAuthor`,
`\NPEERefreshDocumentMetadata`, or ordinary `\hypersetup` keys.

The opening controls can also be applied through `\ExamSetup`:

```tex
\ExamSetup{
  opening/show=true,
  candidate-info/show=false,
  candidate-notices/show=false
}
```

## Question API

```tex
\ExamSection{选择题}
\begin{ExamChoiceQuestion}[id=choice-1,points=5]
  题干……\ExamSelection
  \ExamChoices{$A$}{$B$}{$C$}{$D$}
\end{ExamChoiceQuestion}

\ExamSectionContinue{填空题}
\begin{ExamFillQuestion}[id=fill-1,points=5]
  计算 $\int_0^1 x\,\mathrm{d}x=\ExamBlank$。
\end{ExamFillQuestion}

\ExamSectionContinue{解答题}
\begin{ExamSolutionQuestion}[id=solution-1]{12}
  证明……
\end{ExamSolutionQuestion}
```

`ExamSolutionQuestion` takes question keys as its optional argument and an
optional numeric points argument. The class chooses response-cell geometry
from the solution structure and selected spacing strategy; source papers must
not provide physical heights. A source with no known score can omit the
braced argument; the score is then neither registered nor printed.

Use `ExamSectionContinue` for each later examination section in a generated
paper. It keeps choices, fills, and naturally structured solutions in the same
vertical flow. `ExamSection` is reserved for an explicit new structural start.

The two built-in strategies are selected by the class option:

| Option | Solution behaviour |
| --- | --- |
| `spaced` | Larger body type and relaxed question rhythm; response cells apply only to structured solution layouts. |
| `compact` | No response cells or forced solution page breaks; all questions flow naturally. |

The answer layout is structural rather than question-number based. The default
`pair-first` policy can be changed with `\ExamSetSolutionStructure{natural}` or
`\ExamSetSolutionStructure{full-page}`, and the size of the initial group can
be changed with `\ExamSetSolutionPairCount{2}`. Legacy explicit-height source
syntax is parsed only for migration and is intentionally excluded from the
public API.

Question and structure helpers:

| API | Purpose |
| --- | --- |
| `ExamQuestion` | Generic question wrapper; keys include `id`, `type`, `points`, `show-points` |
| `ExamChoiceQuestion` | Four-option objective question |
| `ExamFillQuestion` | Fill-in question |
| `ExamSolutionQuestion` | Solution question with a response area |
| `ExamSection`, `ExamSectionContinue`, `ExamSolutionHere` | Section headings and transitions |
| `ExamSelection` | Standard choice answer placeholder |
| `ExamBlank` | Standard fill-in line; width is controlled by `blank/width` |
| `ExamChoices{A}{B}{C}{D}` | Automatically selects one-line, 2-by-2, or one-per-line options |
| `ExamChoiceList[columns=1|2|4]` | Arbitrary option list |
| `ExamSubpart{key}` | Numbered `(1)`, `(2)`, ... subpart with a stable reference key |
| `ExamQuestionContinuation` | Intentional continuation indent |
| `ExamQuestionPoints{n}`, `ExamTotalPoints` | Register/print score labels and totals |

The class keeps `cases`, arrays, matrices, vectors, and radicals at their natural
height. Use inline math and never add negative spacing to compensate for a page
or column.

## Figures

Figures are in-flow, never floating:

```tex
\begin{ExamFigure}[
  width=.72\linewidth,
  max-height=.26\textheight,
  align=center,
  alt={函数曲线}
]{build/assets/curve.pdf}
\end{ExamFigure}
```

The single-line form is `\ExamIncludeFigure[width=40mm]{path}`. Supported keys
are `width`, `height`, `max-height`, `align`, `display`, `keep-aspect-ratio`,
`caption`, `alt`, `label`, `before-skip`, `after-skip`, and `options`. A TikZ
figure may be inserted directly in a question body; the JSON/renderer layer
uses the same in-flow contract.

## Math and numbering conventions

Use `$...$` or `\(...\)` for mathematics. With the `inlineonly` option, display
math produces a diagnostic. Fraction size follows position: `\dfrac` in body text,
and `\frac` wherever the current style is already reduced -- a superscript,
subscript, integral bound, or a fraction's own numerator/denominator. `\dfrac` in
any of those slots re-inflates the fraction and overflows the line.
Differentials use `\,\mathrm{d}x`; standard operators use `\sin`, `\cos`,
`\ln`, `\lim`, etc.
For integral regions use the semantic helpers:

```tex
\ExamDoubleIntegral{D},
\ExamTripleIntegral{\Omega},
\ExamContourIntegral{C}
```

These place the supplied region below the integral symbol while preserving the
class's inline-math policy. `ExamCircledDigit`, `ExamCircledItem`, and
`ExamCircledStatement` provide the shared circled-number renderer. For proposition
lists, use the dedicated line commands so ①, ②, ③, and ④ do not run together:

```tex
\ExamStatement{1}{第一条命题内容。}
\ExamStatement{2}{第二条命题内容。}
\ExamStatements{第一条命题内容。}{第二条命题内容。}{第三条命题内容。}{第四条命题内容。}
```

The composition generator applies `\ExamStatementMarker{n}` automatically to
existing numbered proposition sequences in question stems. Circled numbers in
choices, formulas, and diagram labels remain inline but use the same glyph.

## Security mark, footer, and answer modes

```tex
\ExamSetSecurityLevel{3}       % 1=秘密, 2=机密, 3=绝密, 0=关闭
\ExamSetSecurityText{内部资料}  % custom text switches to custom mode
\ExamSetSecurityActivationText{启用前}
\ExamShowSecurityMark
\ExamHideSecurityMark

\ExamSetMode{student}           % student|teacher|key|answer-key
\ExamSetVersion{A}
\ExamVariant{A}{A版内容}{其他版本内容}
\ExamAnswer{C}
\begin{ExamSolution}[解析：]
  解答内容……
\end{ExamSolution}
```

The footer calls the project callback `\ExamFormatFooterContent{label}{page}{total}`;
projects can redefine that callback without changing the class. The class
does not draw publisher-specific footer artwork.

Independent answer books use `ExamAnswerKeyStart`, `ExamAnswerKeySection`,
`ExamAnswerKeyRow`, `ExamAnswerKeySolution`, and `ExamAnswerKeyEnd`.

## Composition JSON mapping

The composition generator resolves a JSON paper reference through
`.npee-math-papers/registry.json` to one paper document in the `.npee-math-papers` store, then emits
a body fragment. It maps fields as follows:

```text
section=choice   -> ExamChoiceQuestion + ExamChoices
section=fill     -> ExamFillQuestion + ExamBlank when a blank marker is present
section=solution -> ExamSolutionQuestion or ExamQuestion + project answer space
subparts        -> ExamSubpart before each ordered item
figures.kind=tikz  -> inline TikZ in the question flow
figures.kind=asset -> ExamFigure/ExamIncludeFigure with a safe relative path
```

The generator, not the class, owns CSV/JSON parsing, group ordering, cover and
back-matter inclusion, appendix insertion, and output filename expansion. The
class receives only the generated `.tex` and its layout/theme options.

## Compatibility and extension policy

`NPEE*` commands remain available for existing sources, but new projects should
use the documented `Exam*` aliases and `/npee_math_papers` setup keys. No command in this
class may assume a particular series, year, publisher, cover, watermark text,
or question bank. Add reusable behavior as a neutral setup key or semantic
environment; keep project content in composition/configuration files.
