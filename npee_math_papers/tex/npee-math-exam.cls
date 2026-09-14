\NeedsTeXFormat{LaTeX2e}[2022-06-01]
% SPDX-License-Identifier: LPPL-1.3c
\ProvidesClass{npee-math-exam}[2026/08/31 v4.7 generic examination template]
\makeatletter

% The generic examination engine is intentionally kept in this class.
% Project-specific text, artwork, and publication profiles remain outside it.

% -----------------------------------------------------------------------------
% Feature section: kernel and engine contract
% -----------------------------------------------------------------------------

% The kernel is the only foundation layer.  It deliberately contains no
% geometry, fonts, artwork, publication strings, or question presentation.
% Feature modules may require it directly when they are used outside the
% orchestration package.
\RequirePackage{iftex}
\ifPDFTeX
  \PackageError{npee-math-exam}{XeLaTeX or LuaLaTeX is required}{%
    npee-math-exam uses Unicode CJK fonts and unicode-math. Run XeLaTeX or
    LuaLaTeX instead of pdfLaTeX.}%
\fi
\RequirePackage{expl3}

% Package-level diagnostics are preferable to class diagnostics in reusable
% .sty modules.  The first argument identifies the owning module, which keeps
% warnings actionable when several feature packages are loaded together.
\newcommand{\NPEEWarning}[2]{\PackageWarning{#1}{#2}}
\newcommand{\NPEEWarningNoLine}[2]{\PackageWarningNoLine{#1}{#2}}
\newcommand{\NPEEError}[3]{\PackageError{#1}{#2}{#3}}

% Shared whitespace normalization used by mode/security/version setters.
\ExplSyntaxOn
\tl_new:N \g_npee_normalized_value_tl
\cs_new_protected:Npn \NPEENormalizeValue #1
  {
    \tl_gset:Nx \g_npee_normalized_value_tl {#1}
    \tl_remove_all:Nn \g_npee_normalized_value_tl {~}
  }
\cs_new:Npn \NPEENormalizedValue
  { \tl_use:N \g_npee_normalized_value_tl }
\ExplSyntaxOff




% -----------------------------------------------------------------------------
% Feature section: runtime state
% -----------------------------------------------------------------------------
\newif\ifNPEEAfour
\newif\ifNPEEAthree
\newif\ifNPEEEyecare
\newif\ifNPEEExamActive
\newif\ifNPEEInlineOnly
\newif\ifNPEEExamFooter
\newif\ifNPEECandidateInfo
\newif\ifNPEECandidateNotices
\newif\ifNPEEPaperOpening
\newif\ifNPEEOpeningPage
\newif\ifNPEEWatermarkEnabled
\newif\ifNPEEConfidentialMarkEnabled
\newif\ifNPEEConfidentialMarkPending
\newif\ifNPEEConfidentialMarkActive
\newif\ifNPEESecurityCustomText
\newif\ifNPEEAnswerMode
\newif\ifNPEEExamColumnsOpen
\newif\ifNPEEInAnswerCell
\newif\ifNPEEExamWatermark
\newif\ifNPEEExamSpread
\newif\ifNPEECompact
\newif\ifNPEEAfourBlank
\newif\ifNPEEAnswerLayout
\newif\ifNPEECollectionContentsEnabled
\newif\ifNPEECollectionGroupContentsEnabled
\newif\ifNPEECollectionPaperContentsEnabled
\NPEEAfourfalse
\NPEEAthreefalse
\NPEEEyecarefalse
\NPEEExamActivefalse
\NPEEInlineOnlyfalse
\NPEEExamFooterfalse
\NPEECandidateInfotrue
\NPEECandidateNoticestrue
\NPEEPaperOpeningtrue
\NPEEOpeningPagefalse
\NPEEWatermarkEnabledtrue
\NPEEConfidentialMarkEnabledtrue
\NPEEConfidentialMarkPendingfalse
\NPEEConfidentialMarkActivefalse
\NPEESecurityCustomTextfalse
\NPEEAnswerModefalse
\NPEEExamColumnsOpenfalse
\NPEEInAnswerCellfalse
\NPEEExamWatermarkfalse
\NPEEExamSpreadfalse
\NPEECompactfalse
\NPEEAfourBlankfalse
\NPEEAnswerLayouttrue
\NPEECollectionContentsEnabledfalse
\NPEECollectionGroupContentsEnabledtrue
\NPEECollectionPaperContentsEnabledtrue




% -----------------------------------------------------------------------------
% Feature section: legacy option state
% -----------------------------------------------------------------------------

% This package is intentionally outside the runtime state layer.  It exists
% only for old sources that encoded subject identity as class options;
% document-level publication profiles do not need it directly.

\newif\ifNPEEMathOne
\newif\ifNPEEMathTwo
\newif\ifNPEEMathThree
\NPEEMathOnefalse
\NPEEMathTwofalse
\NPEEMathThreefalse

\newcommand{\NPEELegacySubjectKey}{math1}
\newcommand{\NPEELayoutLabel}{a3}
\newcommand{\NPEEThemeLabel}{print}

\newcommand{\NPEESelectMathOne}{%
  \NPEEMathOnetrue
  \NPEEMathTwofalse
  \NPEEMathThreefalse
  \renewcommand{\NPEELegacySubjectKey}{math1}}
\newcommand{\NPEESelectMathTwo}{%
  \NPEEMathOnefalse
  \NPEEMathTwotrue
  \NPEEMathThreefalse
  \renewcommand{\NPEELegacySubjectKey}{math2}}
\newcommand{\NPEESelectMathThree}{%
  \NPEEMathOnefalse
  \NPEEMathTwofalse
  \NPEEMathThreetrue
  \renewcommand{\NPEELegacySubjectKey}{math3}}




% -----------------------------------------------------------------------------
% Feature section: class options
% -----------------------------------------------------------------------------

% Option parsing is separate from runtime state.  This keeps the state module
% usable by a downstream document driver that configures values directly.

% Subject options remain accepted for old sources, but are
% intentionally marked as compatibility selectors.  New projects inject
% their keys through a document-level publication profile.
\DeclareOption{math1}{\NPEESelectMathOne}
\DeclareOption{math2}{\NPEESelectMathTwo}
\DeclareOption{math3}{\NPEESelectMathThree}

\DeclareOption{a4}{%
  \NPEEAfourtrue
  \NPEEAthreefalse
  \NPEEAfourBlankfalse
  \renewcommand{\NPEELayoutLabel}{a4}}
\DeclareOption{a3}{%
  % A3 is a landscape two-page spread with the established spread flow contract
  % retaining its own physical stock and output label.
  \NPEEAfourfalse
  \NPEEAthreetrue
  \NPEEAfourBlankfalse
  \renewcommand{\NPEELayoutLabel}{a3}}
\DeclareOption{print}{%
  \NPEEEyecarefalse
  \renewcommand{\NPEEThemeLabel}{print}}
\DeclareOption{normal}{%
  \NPEEEyecarefalse
  \renewcommand{\NPEEThemeLabel}{print}}
\DeclareOption{eyecare}{%
  \NPEEEyecaretrue
  \renewcommand{\NPEEThemeLabel}{eyecare}}
\DeclareOption{eye}{%
  \NPEEEyecaretrue
  \renewcommand{\NPEEThemeLabel}{eyecare}}
\DeclareOption{cream}{%
  \NPEEEyecaretrue
  \renewcommand{\NPEEThemeLabel}{cream}}
\DeclareOption{white}{%
  \NPEEEyecarefalse
  \renewcommand{\NPEEThemeLabel}{print}}
\DeclareOption{compact}{\NPEEAfourBlankfalse\NPEECompacttrue}
\DeclareOption{spaced}{\NPEEAfourBlankfalse\NPEECompactfalse}
\DeclareOption{a4-blank}{%
  \NPEEAfourtrue
  \NPEEAthreefalse
  \NPEEAfourBlanktrue
  \NPEECompacttrue
  \NPEEAnswerLayoutfalse
  \renewcommand{\NPEELayoutLabel}{a4}}
\DeclareOption{inlineonly}{\NPEEInlineOnlytrue}
\DeclareOption{candidateinfo}{\NPEECandidateInfotrue}
\DeclareOption{nocandidateinfo}{\NPEECandidateInfofalse}
\DeclareOption{candidatenotices}{\NPEECandidateNoticestrue}
\DeclareOption{nocandidatenotices}{\NPEECandidateNoticesfalse}
\DeclareOption{opening}{\NPEEPaperOpeningtrue}
\DeclareOption{noopening}{\NPEEPaperOpeningfalse}
\DeclareOption{watermark}{\NPEEWatermarkEnabledtrue}
\DeclareOption{nowatermark}{\NPEEWatermarkEnabledfalse}
\DeclareOption{securitymark}{\NPEEConfidentialMarkEnabledtrue}
\DeclareOption{nosecuritymark}{\NPEEConfidentialMarkEnabledfalse}
\DeclareOption{confidentialmark}{\NPEEConfidentialMarkEnabledtrue}
\DeclareOption{noconfidentialmark}{\NPEEConfidentialMarkEnabledfalse}
\DeclareOption{answers}{\NPEEAnswerModetrue}
\DeclareOption{noanswers}{\NPEEAnswerModefalse}
\DeclareOption*{\NPEEWarning{npee-math-exam}{Unknown option `\CurrentOption' ignored}}

% Process class options after all state selectors are declared.
\ExecuteOptions{a3,print,spaced}
\ProcessOptions\relax
\LoadClass[UTF8,oneside,fontset=none]{ctexart}

% Strict inline-math mode for compact exam layouts.  In this mode every
% display-math entry point emits an actionable diagnostic.  The \[...\]
% delimiter has an inline recovery path so a source compiled without
% -halt-on-error still remains in paragraph flow; the build scripts reject
% the source before compilation, so no block formula can enter a release PDF.
% Structures such as cases/array/gathered remain valid when nested in
% \(...\), which is the intended way to typeset tall mathematics here.
\newcommand{\NPEEInstallInlineOnlyGuard}{%
  \ifNPEEInlineOnly
    \protected\def\[{%
      \NPEEError{npee-math-exam}{Block math is disabled by the inlineonly option}{%
        Use \string\(\string\displaystyle ... \string\) or a semantic inline
        structure such as cases/array inside \string\( ... \string\).}%
      \(\displaystyle
    }%
    \protected\def\]{\)}%
    \everydisplay\expandafter{\the\everydisplay
      \NPEEError{npee-math-exam}{A display-math environment was used while inlineonly is active}{%
        Replace equation/align/$$ with inline math.}%
    }%
  \fi
}
\AtBeginDocument{\NPEEInstallInlineOnlyGuard}




% -----------------------------------------------------------------------------
% Feature section: lifecycle hooks
% -----------------------------------------------------------------------------

% These hooks are the dependency-inversion boundary between the paper
% lifecycle and optional front-matter features.  A paper can therefore be
% typeset without loading candidate information or per-paper PDF metadata.
% Hooks are named after lifecycle phases rather than implementation packages.
% Feature modules may register here without forcing the lifecycle to require
% them, which keeps focused package use possible in downstream templates.
\NewHook{npee-exam/book-body/begin}
\NewHook{npee-exam/paper/before-start}
\NewHook{npee-exam/paper/start}
\NewHook{npee-exam/paper/end}
\NewHook{npee-exam/paper/bookmark}
\NewHook{npee-exam/paper/opening}
\NewHook{npee-exam/transition}




% -----------------------------------------------------------------------------
% Feature section: semantic counters
% -----------------------------------------------------------------------------

% Semantic document counters are independent of geometry and rendering.  A
% metadata-only or answer-only package can therefore refer to paper/question
% identities without pulling in multicol or changing the page layout.

\newcounter{npeeexampaper}
\newcounter{npeeexamsection}[npeeexampaper]
\newcounter{npeeexamquestion}[npeeexampaper]
% Ordinal within the solution section.  Pagination is based on this
% structure counter rather than on a publication's global question numbers.
\newcounter{npeesolutionquestion}[npeeexampaper]
\newcounter{npeesubpart}[npeeexamquestion]
\newcounter{npeecircleditem}[npeeexamquestion]
\newcounter{npeechoice}
\newcounter{npeelogicalpage}
\newcounter{npeetotalpoints}[npeeexampaper]

% Supply stable hyper anchors whether hyperref is loaded before or after this
% package.  The paper and question components make the subordinate anchors
% unique across a collection.
\providecommand{\theHnpeesubpart}{}
\providecommand{\theHnpeecircleditem}{}
\renewcommand{\theHnpeesubpart}{%
  \arabic{npeeexampaper}.\arabic{npeeexamquestion}.\arabic{npeesubpart}}
\renewcommand{\theHnpeecircleditem}{%
  \arabic{npeeexampaper}.\arabic{npeeexamquestion}.\arabic{npeecircleditem}}




% -----------------------------------------------------------------------------
% Feature section: setup registry
% -----------------------------------------------------------------------------

% This package owns only the global key namespace and its registration API.
% Feature packages register their own keys when they are loaded, so the
% settings layer never needs to load an implementation package in reverse.
\RequirePackage{pgfkeys}

\pgfkeys{
  /npee/.is family,
  /npee/.unknown/.code={%
    \NPEEWarning{npee-math-exam}{%
      Unknown setup key `\pgfkeyscurrentname' ignored}}
}

% Public extension points for first-party and downstream capability packages.
% The plural form accepts ordinary pgfkeys declarations relative to /npee.
\newcommand{\NPEEDeclareSetupKeys}[1]{\pgfkeys{/npee/.cd,#1}}
\newcommand{\NPEEDeclareSetupKey}[2]{%
  \pgfkeys{/npee/#1/.code={#2}}}
\newcommand{\NPEEDeclareSetupStyle}[2]{%
  \pgfkeys{/npee/#1/.style={#2}}}
\newcommand{\NPEEDeclareSetupIf}[2]{%
  \pgfkeys{/npee/#1/.is if=#2}}

\newcommand{\NPEESetup}[1]{\pgfkeys{/npee/.cd,#1}}
\providecommand{\ExamSetup}{\NPEESetup}




% -----------------------------------------------------------------------------
% Feature section: locale and labels
% -----------------------------------------------------------------------------

% Number conversion is isolated from ctexart.  Feature modules consume these
% semantic formatters instead of relying on the class-only \chinese command.
\RequirePackage{zhnumber}
\newcommand{\NPEEChineseCounter}[1]{\zhnumber{\arabic{#1}}}
\newcommand{\NPEEFormatPaperNumber}{\NPEEChineseCounter{npeeexampaper}}
\newcommand{\NPEEFormatSectionNumber}{\NPEEChineseCounter{npeeexamsection}}

% Section punctuation is a locale/style token, not part of the question-flow
% implementation.  The defaults reproduce the Chinese examination convention;
% a downstream locale can replace all three tokens without redefining the
% section renderer.
\newcommand{\NPEESectionNumberSeparator}{、}
\newcommand{\NPEESectionTitleSeparator}{：}
\newcommand{\NPEESectionTerminalPunctuation}{。}
\newcommand{\NPEELabelSeparator}{：}
\newcommand{\NPEELeftParenthesis}{（}
\newcommand{\NPEERightParenthesis}{）}
\newcommand{\NPEESetLocaleDelimiters}[3]{%
  \renewcommand{\NPEESectionNumberSeparator}{#1}%
  \renewcommand{\NPEESectionTitleSeparator}{#2}%
  \renewcommand{\NPEESectionTerminalPunctuation}{#3}}

\NPEEDeclareSetupKeys{
  locale/section-number-separator/.code={%
    \renewcommand{\NPEESectionNumberSeparator}{#1}},
  locale/section-title-separator/.code={%
    \renewcommand{\NPEESectionTitleSeparator}{#1}},
  locale/section-terminal-punctuation/.code={%
    \renewcommand{\NPEESectionTerminalPunctuation}{#1}},
  locale/label-separator/.code={%
    \renewcommand{\NPEELabelSeparator}{#1}},
  locale/left-parenthesis/.code={%
    \renewcommand{\NPEELeftParenthesis}{#1}},
  locale/right-parenthesis/.code={%
    \renewcommand{\NPEERightParenthesis}{#1}}
}




% -----------------------------------------------------------------------------
% Feature section: neutral palette
% -----------------------------------------------------------------------------

% This module contains only reusable colour names.  Publication artwork and
% visible branding belong to the document project, not to the class stack.
\RequirePackage{xcolor}

% Formal examination stock: a pale warm yellow with a readable warm-black ink.
% Projects may override either token without changing the layout engine.
\definecolor{NPEEEyePage}{HTML}{FFF9E2}
\definecolor{NPEEEyeText}{HTML}{322D26}
\newcommand{\NPEESetEyecarePaperColor}[1]{\colorlet{NPEEEyePage}{#1}}
\newcommand{\NPEESetEyecareTextColor}[1]{\colorlet{NPEEEyeText}{#1}}
\newcommand{\NPEESetEyecarePalette}[2]{%
  \NPEESetEyecarePaperColor{#1}%
  \NPEESetEyecareTextColor{#2}}

\NPEEDeclareSetupKeys{
  eyecare/paper-color/.code={\NPEESetEyecarePaperColor{#1}},
  eyecare/text-color/.code={\NPEESetEyecareTextColor{#1}}
}




% -----------------------------------------------------------------------------
% Feature section: PDF metadata and bookmarks
% -----------------------------------------------------------------------------

% PDF destinations and document metadata are a separate capability so a
% downstream publisher can replace the driver or omit them in a plain print
% build without loading the examination layout modules.
\RequirePackage[unicode,bookmarksopen=true,bookmarksnumbered=false]{hyperref}

\providecommand{\NPEEDocumentAuthor}{}
\providecommand{\NPEEPdfTitle}{}
\providecommand{\NPEEPdfAuthor}{}
\providecommand{\NPEEPdfSubject}{}

\hypersetup{
  pdftitle={\NPEEPdfTitle},
  pdfauthor={\NPEEPdfAuthor},
  pdfsubject={\NPEEPdfSubject},
  colorlinks=false,
  pdfborder={0 0 0}}

\newcounter{npeebookmark}
\newcommand{\NPEEBookmarkAtLevel}[3]{%
  \phantomsection
  \stepcounter{npeebookmark}%
  \pdfbookmark[#1]{#2}{npee.bookmark.#3.\arabic{npeebookmark}}}
\newcommand{\NPEEBookmark}[2]{\NPEEBookmarkAtLevel{0}{#1}{#2}}
% Write a visible table-of-contents entry without asking hyperref to create a
% second outline item. Explicit NPEEBookmark calls remain the single outline
% source for collections, groups, and papers.
\newcommand{\NPEEAddContentsEntry}[2]{%
  \addtocontents{toc}{%
    \protect\contentsline{#1}{#2}{\thepage}{\@currentHref}\protected@file@percent}}

\newcommand{\NPEESetDocumentAuthor}[1]{%
  \renewcommand{\NPEEDocumentAuthor}{#1}%
  \renewcommand{\NPEEPdfAuthor}{#1}}
\newcommand{\NPEERefreshDocumentMetadata}{%
  \hypersetup{
    pdftitle={\NPEEPdfTitle},
    pdfauthor={\NPEEPdfAuthor},
    pdfsubject={\NPEEPdfSubject}}}
\newcommand{\NPEEDeclarePublication}{\NPEERefreshDocumentMetadata}




% -----------------------------------------------------------------------------
% Feature section: typography
% -----------------------------------------------------------------------------

% Engine validation and diagnostics have one owner.  Loading the typography
% package directly therefore produces the same actionable error as the class.
\RequirePackage{fontspec}
\RequirePackage{unicode-math}

\defaultfontfeatures{Ligatures=TeX}
% Conventional examination fonts: Times-like Latin and mathematics, with a
% robust CJK fallback chain for Windows, TeX Live, macOS and Linux.
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
\IfFontExistsTF{Arial}{\setsansfont{Arial}}{\setsansfont{TeX Gyre Heros}}
% The reference examination source uses Cambria Math.  Prefer it when the
% Windows font is available so radicals, integral signs, delimiters and
% operator spacing follow the reference instead of the narrower Termes
% substitute.  Keep a portable fallback for non-Windows XeLaTeX builds.
\IfFontExistsTF{Cambria Math}{%
  \setmathfont{Cambria Math}%
}{%
  \IfFontExistsTF{TeX Gyre Termes Math}{%
    \setmathfont{TeX Gyre Termes Math}%
  }{%
    \setmathfont{Latin Modern Math}%
  }%
}
\newcommand{\NPEESetSafeCJKSans}{%
  \IfFontExistsTF{Microsoft YaHei}{%
    \IfFontExistsTF{Microsoft YaHei Bold}{%
      \setCJKsansfont[BoldFont=Microsoft YaHei Bold]{Microsoft YaHei}%
    }{\setCJKsansfont{Microsoft YaHei}}%
  }{%
    \IfFontExistsTF{FandolHei}{\setCJKsansfont{FandolHei}}{\setCJKsansfont{SimSun}}%
  }}
\IfFontExistsTF{SimSun}{%
  \IfFontExistsTF{SimHei}{%
    \setCJKmainfont[BoldFont=SimHei]{SimSun}%
    \newCJKfontfamily\NPEEBodyFace[BoldFont=SimHei]{SimSun}%
    \newCJKfontfamily\NPEEHeadingFace{SimHei}%
  }{%
    \setCJKmainfont{SimSun}%
    \newCJKfontfamily\NPEEBodyFace{SimSun}%
    \IfFontExistsTF{Microsoft YaHei}{%
      \IfFontExistsTF{Microsoft YaHei Bold}{%
        \newCJKfontfamily\NPEEHeadingFace[BoldFont=Microsoft YaHei Bold]{Microsoft YaHei}%
      }{\newCJKfontfamily\NPEEHeadingFace{Microsoft YaHei}}%
    }{%
      \IfFontExistsTF{FandolHei}{\newCJKfontfamily\NPEEHeadingFace{FandolHei}}{\newCJKfontfamily\NPEEHeadingFace{SimSun}}%
    }%
  }%
  \NPEESetSafeCJKSans
  \newfontfamily\NPEECircledFace{SimSun}%
}{%
  \IfFontExistsTF{Noto Serif CJK SC}{%
    \IfFontExistsTF{Noto Sans CJK SC}{%
      \setCJKmainfont[BoldFont=Noto Sans CJK SC]{Noto Serif CJK SC}%
      \setCJKsansfont{Noto Sans CJK SC}%
      \newCJKfontfamily\NPEEBodyFace{Noto Serif CJK SC}%
      \newCJKfontfamily\NPEEHeadingFace{Noto Sans CJK SC}%
    }{%
      \setCJKmainfont{Noto Serif CJK SC}%
      \setCJKsansfont{Noto Serif CJK SC}%
      \newCJKfontfamily\NPEEBodyFace{Noto Serif CJK SC}%
      \newCJKfontfamily\NPEEHeadingFace{Noto Serif CJK SC}%
    }%
    \newfontfamily\NPEECircledFace{Noto Serif CJK SC}%
  }{%
    \setCJKmainfont{FandolSong}%
    \newCJKfontfamily\NPEEBodyFace{FandolSong}%
    \IfFontExistsTF{FandolHei}{%
      \setCJKsansfont{FandolHei}%
      \newCJKfontfamily\NPEEHeadingFace{FandolHei}%
    }{%
      \setCJKsansfont{FandolSong}%
      \newCJKfontfamily\NPEEHeadingFace{FandolSong}%
    }%
    \newfontfamily\NPEECircledFace{FandolSong}%
  }%
}
% Circled digits are CJK punctuation in source papers.
\renewcommand{\NPEECircledFace}{\NPEEBodyFace}




% -----------------------------------------------------------------------------
% Feature section: A3/A4 layout
% -----------------------------------------------------------------------------

\RequirePackage{geometry}
\RequirePackage{multicol}
\ifNPEEAthree
  \geometry{paperwidth=420mm,paperheight=297mm,left=26mm,right=26mm,top=13mm,bottom=28mm,
    headheight=0pt,headsep=0pt,footskip=8mm,includefoot}
\else\ifNPEEAfour
  \geometry{a4paper,left=18mm,right=18mm,top=18mm,bottom=30mm,
    headheight=0pt,headsep=0pt,footskip=9mm,includefoot}
\else
  \geometry{paperwidth=372.5mm,paperheight=257.9mm,left=23mm,right=23mm,
    top=11mm,bottom=25mm,headheight=0pt,headsep=0pt,footskip=8mm,includefoot}
\fi\fi
\newcommand{\NPEESetMargins}[4]{\geometry{left=#1,right=#2,top=#3,bottom=#4}}

% The public multicols \columnbreak macro contains its own conditionals.  A
% forced penalty can make the output routine run before those \fi tokens are
% consumed, so emit the default forced-break penalty directly.  Resolve the
% mode test first and insert the penalty only after all conditionals close.
\newcommand{\NPEESafeColumnBreak}{%
  \def\NPEESafeColumnBreakAction{\penalty -\@Mv}%
  \ifvmode
  \else
    \def\NPEESafeColumnBreakAction{\vadjust{\penalty -\@Mv}}%
  \fi
  \NPEESafeColumnBreakAction}

% A3 uses a two-column spread for exam bodies; A4 is one continuous
% column per physical page. Collection contents use a denser three-column
% presentation and therefore have their own environment below.
% The same public flow commands are kept for paper sources, but their A4
% implementation deliberately turns a requested column transition into a
% physical page transition.  This lets source content flow naturally until a
  % paper explicitly starts a new logical page, while preserving the spread
  % contract and its central rule.
\newcommand{\NPEEExamPageBreak}{%
  % Resolve the requested transition before entering a multicols output
  % routine.  Executing \columnbreak while either conditional is still open
  % can leave TeX's \if stack unbalanced when multicols ships the column.
  \def\NPEEPageBreakAction{\clearpage}%
  \ifNPEEAfour
  \else
    \ifNPEEExamColumnsOpen
      \def\NPEEPageBreakAction{\NPEESafeColumnBreak}%
    \fi
  \fi
  \NPEEPageBreakAction\ignorespaces}
\newcommand{\NPEESectionTitleSize}{13.5pt}
\newcommand{\NPEESectionTitleLineHeight}{18.5pt}
\newcommand{\NPEESetSectionTitleStyle}[2]{%
  \renewcommand{\NPEESectionTitleSize}{#1}%
  \renewcommand{\NPEESectionTitleLineHeight}{#2}}

% Reference exam typography uses a compact ten-point body with restrained leading.
% The named parameters remain overridable for papers with different stock sizes.
\newcommand{\NPEEBodyFontSize}{12pt}
\newcommand{\NPEEBodyLineHeight}{18pt}
\newcommand{\NPEEApplyBodyStyle}{\fontsize{\NPEEBodyFontSize}{\NPEEBodyLineHeight}\selectfont}
\newcommand{\NPEESetBodyFontSize}[2]{%
  \renewcommand{\NPEEBodyFontSize}{#1}%
  \renewcommand{\NPEEBodyLineHeight}{#2}%
  \NPEEApplyBodyStyle}
\setlength{\columnsep}{14mm}
% Render the spread divider as a page overlay so it starts below the header.
\newlength{\NPEEDividerWidth}
\setlength{\NPEEDividerWidth}{.35pt}
\ifNPEEAfour\setlength{\columnseprule}{0pt}\else\setlength{\columnseprule}{0pt}\fi
\raggedcolumns
\raggedbottom
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\setlength{\mathsurround}{0pt}

% Spacing is a document-level presentation choice.  Both modes share the same
% body typography; the target policy below changes solution pagination, while
% these rhythm tokens keep question blocks visually consistent.
\newcommand{\NPEEQuestionBeforeSkip}{1.6mm}
\newcommand{\NPEESectionBeforeSkip}{2.4mm}
\newcommand{\NPEEChoiceBeforeSkip}{1mm}
\newcommand{\NPEESubpartBeforeSkip}{2mm}
\newcommand{\NPEESetSpacedSpacing}{%
  \NPEECompactfalse
  \NPEEAnswerLayouttrue
  \renewcommand{\NPEEBodyLineHeight}{18pt}%
  \renewcommand{\NPEEQuestionBeforeSkip}{1.6mm}%
  \renewcommand{\NPEESectionBeforeSkip}{2.4mm}%
  \renewcommand{\NPEEChoiceBeforeSkip}{1mm}%
  \renewcommand{\NPEESubpartBeforeSkip}{2mm}%
  \NPEEApplyBodyStyle}
\newcommand{\NPEESetCompactSpacing}{%
  \NPEECompacttrue
  \NPEEAnswerLayoutfalse
  \renewcommand{\NPEEBodyLineHeight}{18pt}%
  \renewcommand{\NPEEQuestionBeforeSkip}{1.6mm}%
  \renewcommand{\NPEESectionBeforeSkip}{2.4mm}%
  \renewcommand{\NPEEChoiceBeforeSkip}{1mm}%
  \renewcommand{\NPEESubpartBeforeSkip}{2mm}%
  \NPEEApplyBodyStyle}
\newcommand{\NPEEApplySpacingMode}{%
  \ifNPEECompact\NPEESetCompactSpacing\else\NPEESetSpacedSpacing\fi}
\newcommand{\NPEESetSpacingMode}[1]{%
  \edef\NPEETempSpacingMode{#1}%
  \ifnum\pdfstrcmp{\NPEETempSpacingMode}{compact}=0
    \NPEEAfourBlankfalse
    \NPEESetCompactSpacing
  \else
    \ifnum\pdfstrcmp{\NPEETempSpacingMode}{spaced}=0
      \NPEEAfourBlankfalse
      \NPEESetSpacedSpacing
    \else
      \ifnum\pdfstrcmp{\NPEETempSpacingMode}{a4-blank}=0
        \NPEEAfourBlanktrue
        \NPEESetCompactSpacing
      \else
        \NPEEWarningNoLine{npee-math-exam}{Unknown spacing mode `#1'; using spaced}%
        \NPEEAfourBlankfalse
        \NPEESetSpacedSpacing
      \fi
    \fi
  \fi}
\newcommand{\NPEEApplyTargetSpacingPolicy}[1]{%
  \edef\NPEETargetSpacing{#1}%
  \ifnum\pdfstrcmp{\NPEETargetSpacing}{compact}=0
    \NPEEAfourBlankfalse
    \NPEESetSolutionStructure{natural}%
    \NPEESetCompactSpacing
  \else
    \ifnum\pdfstrcmp{\NPEETargetSpacing}{spaced}=0
      \NPEEAfourBlankfalse
      \NPEESetSolutionStructure{pair-first}%
      \NPEESetSolutionPairCount{2}%
      \NPEESetSpacedSpacing
    \else
      \ifnum\pdfstrcmp{\NPEETargetSpacing}{a4-blank}=0
        \NPEEAfourBlanktrue
        \NPEESetSolutionStructure{natural}%
        \NPEESetCompactSpacing
      \else
        \NPEEWarningNoLine{npee-math-exam}{Unknown target spacing policy `#1'; using spaced}%
        \NPEEAfourBlankfalse
        \NPEESetSolutionStructure{pair-first}%
        \NPEESetSolutionPairCount{2}%
        \NPEESetSpacedSpacing
      \fi
    \fi
  \fi}
\NPEEApplySpacingMode
% -----------------------------------------------------------------------------
% Feature section: mathematical operator conventions
% -----------------------------------------------------------------------------

% unicode-math defines the multiple-integral glyphs as Unicode math symbols.
% Wrapping them as limited operators gives region labels the familiar
% examination-mathematics layout. Explicit limits are intentional, so the
% region appears directly below the integral sign even in inline displaystyle math.
% The original glyphs are saved first, so the wrappers never recurse.
\let\NPEEOriginalDoubleIntegral\iint
\let\NPEEOriginalTripleIntegral\iiint
\let\NPEEOriginalQuadrupleIntegral\iiiint
\let\NPEEOriginalContourIntegral\oint
% Standard LaTeX defines limits as ordinary (side-scripted) math operators
% in inline mathematics.  Examination sources use compact inline formulas but
% still expect the limit set directly below the operator, just as in display
% mathematics.  Save the original token only for compatibility/debugging and
% install a portable operator wrapper with explicit limits.
\let\NPEEOriginalLimit\lim
\protected\def\lim{\mathop{\mathrm{lim}}\limits}
\let\NPEEOriginalLimitSup\limsup
\protected\def\limsup{\mathop{\mathrm{lim\,sup}}\limits}
\let\NPEEOriginalLimitInf\liminf
\protected\def\liminf{\mathop{\mathrm{lim\,inf}}\limits}
\let\NPEEOriginalSum\sum
\let\NPEEOriginalProd\prod
\let\NPEEOriginalBigcap\bigcap
\let\NPEEOriginalBigcup\bigcup
\protected\def\sum{\mathop{\displaystyle\NPEEOriginalSum}\limits}
\protected\def\prod{\mathop{\displaystyle\NPEEOriginalProd}\limits}
\protected\def\bigcap{\mathop{\displaystyle\NPEEOriginalBigcap}\limits}
\protected\def\bigcup{\mathop{\displaystyle\NPEEOriginalBigcup}\limits}
\let\NPEEOriginalMax\max
\let\NPEEOriginalMin\min
\let\NPEEOriginalSup\sup
\let\NPEEOriginalInf\inf
\protected\def\max{\mathop{\mathrm{max}}\limits}
\protected\def\min{\mathop{\mathrm{min}}\limits}
\protected\def\sup{\mathop{\mathrm{sup}}\limits}
\protected\def\inf{\mathop{\mathrm{inf}}\limits}
\protected\def\iint{\mathop{\displaystyle\NPEEOriginalDoubleIntegral}\limits}
\protected\def\iiint{\mathop{\displaystyle\NPEEOriginalTripleIntegral}\limits}
\protected\def\iiiint{\mathop{\displaystyle\NPEEOriginalQuadrupleIntegral}\limits}
\protected\def\oint{\mathop{\displaystyle\NPEEOriginalContourIntegral}\limits}

% Some Cambria Math installations do not expose the optional surface/volume
% contour glyphs.  Keep the public API available everywhere, using the closest
% standard multiple-integral glyph as a portable fallback in that case.
\@ifundefined{oiint}{%
  \let\NPEEOriginalSurfaceIntegral\NPEEOriginalDoubleIntegral
}{%
  \let\NPEEOriginalSurfaceIntegral\oiint
  \protected\def\oiint{\mathop{\displaystyle\NPEEOriginalSurfaceIntegral}\limits}
}
\@ifundefined{oiiint}{%
  \let\NPEEOriginalVolumeContourIntegral\NPEEOriginalTripleIntegral
}{%
  \let\NPEEOriginalVolumeContourIntegral\oiiint
  \protected\def\oiiint{\mathop{\displaystyle\NPEEOriginalVolumeContourIntegral}\limits}
}

% Public commands are useful when a source wants to make the intended region
% explicit, while the redefinitions above keep existing ``\iint_D`` sources
% compatible without per-question edits.
\newcommand{\NPEEIntegralWithRegion}[2]{%
  \mathop{\displaystyle#1}\limits_{#2}%
}
\newcommand{\NPEEDoubleIntegral}[1]{%
  \mathop{\displaystyle\NPEEOriginalDoubleIntegral}\limits_{#1}%
}
\newcommand{\NPEETripleIntegral}[1]{%
  \mathop{\displaystyle\NPEEOriginalTripleIntegral}\limits_{#1}%
}
\newcommand{\NPEEQuadrupleIntegral}[1]{%
  \mathop{\displaystyle\NPEEOriginalQuadrupleIntegral}\limits_{#1}%
}
\newcommand{\NPEEContourIntegral}[1]{%
  \mathop{\displaystyle\NPEEOriginalContourIntegral}\limits_{#1}%
}
\newcommand{\NPEESurfaceIntegral}[1]{%
  \mathop{\displaystyle\NPEEOriginalSurfaceIntegral}\limits_{#1}%
}
\newcommand{\NPEEVolumeContourIntegral}[1]{%
  \mathop{\displaystyle\NPEEOriginalVolumeContourIntegral}\limits_{#1}%
}
\newcommand{\NPEESetColumnGap}[1]{\setlength{\columnsep}{#1}}
\newcommand{\NPEESetColumnRule}[1]{%
  \setlength{\NPEEDividerWidth}{#1}%
  \setlength{\columnseprule}{0pt}}
\newcommand{\NPEEDrawExamDivider}{%
  \begin{tikzpicture}[remember picture,overlay]
    \draw[line width=\NPEEDividerWidth]
      ([yshift=-19mm]current page.north) --
      ([yshift=30mm]current page.south);
  \end{tikzpicture}}
\newcommand{\NPEEExamBeginColumns}{%
  \def\NPEEBeginColumnsAction{}%
  \ifNPEEAfour
    % A4's body is intentionally a normal single-column paragraph flow.
  \else
    \ifNPEEExamColumnsOpen
    \else
      \def\NPEEBeginColumnsAction{\begin{multicols*}{2}\global\NPEEExamColumnsOpentrue}%
    \fi
  \fi
  \NPEEBeginColumnsAction}
\newcommand{\NPEEExamEndColumns}{%
  \def\NPEEEndColumnsAction{}%
  \ifNPEEAfour
    % There is no column environment to close in A4 mode.
  \else
    \ifNPEEExamColumnsOpen
      \def\NPEEEndColumnsAction{\end{multicols*}\global\NPEEExamColumnsOpenfalse}%
    \fi
  \fi
  \NPEEEndColumnsAction}
\newcommand{\NPEEExamColumnBreak}{%
  % As above, choose the action while conditionals are closed, then invoke
  % the output routine.  This is important for automatic solution breaks.
  \def\NPEEColumnBreakAction{\clearpage}%
  \ifNPEEAfour
  \else
    \ifNPEEExamColumnsOpen
      \def\NPEEColumnBreakAction{\NPEESafeColumnBreak}%
    \fi
  \fi
  \NPEEColumnBreakAction\ignorespaces}

% The table of contents is a navigation surface rather than exam content.  A3
% uses four columns to keep the long paper list compact, without
% changing the two-column body contract used by every paper.
\newcommand{\NPEECollectionContentsBeginColumns}{%
  \def\NPEEContentsBeginColumnsAction{}%
  \ifNPEEAthree
    \def\NPEEContentsBeginColumnsAction{\begin{multicols*}{4}}%
  \else
    \ifNPEEAfour
    \else
      \def\NPEEContentsBeginColumnsAction{\begin{multicols*}{3}}%
    \fi
  \fi
  \NPEEContentsBeginColumnsAction}
\newcommand{\NPEECollectionContentsEndColumns}{%
  \def\NPEEContentsEndColumnsAction{}%
  \ifNPEEAthree
    \def\NPEEContentsEndColumnsAction{\end{multicols*}}%
  \else
    \ifNPEEAfour
    \else
      \def\NPEEContentsEndColumnsAction{\end{multicols*}}%
    \fi
  \fi
  \NPEEContentsEndColumnsAction}

\NPEEDeclareSetupKeys{
  body/font-size/.code={%
    \renewcommand{\NPEEBodyFontSize}{#1}\NPEEApplyBodyStyle},
  body/line-height/.code={%
    \renewcommand{\NPEEBodyLineHeight}{#1}\NPEEApplyBodyStyle},
  body/.style={body/font-size={#1}},
  section/font-size/.code={\renewcommand{\NPEESectionTitleSize}{#1}},
  section/line-height/.code={\renewcommand{\NPEESectionTitleLineHeight}{#1}},
  column/gap/.code={\NPEESetColumnGap{#1}},
  column/rule/.code={\NPEESetColumnRule{#1}},
  spacing/mode/.code={\NPEESetSpacingMode{#1}}
}
% Front matter keeps the original white stock.  The examination lifecycle
% switches to the eyecare palette when the body starts.
\AtBeginDocument{\NPEEApplyBodyStyle}




% -----------------------------------------------------------------------------
% Feature section: pagination
% -----------------------------------------------------------------------------

% Pagination is deliberately independent from footer artwork.  The lifecycle
% uses this module to learn a paper's logical page total; a different renderer
% may consume the same total without loading TikZ or the footer package.

\newif\ifNPEEPageCountAutomatic
\NPEEPageCountAutomatictrue
\newcommand{\NPEEPageCount}{8}
\newcommand{\NPEEUpdateOpeningPageState}{%
  \global\NPEEOpeningPagefalse
  \ifNPEEPaperOpening
    \ifNPEECandidateInfo
      \global\NPEEOpeningPagetrue
    \else\ifNPEECandidateNotices
      \global\NPEEOpeningPagetrue
    \fi\fi
  \fi}
\newcommand{\NPEEUpdateDefaultPageCount}{%
  \NPEEUpdateOpeningPageState
  \ifNPEEPageCountAutomatic
    \ifNPEEAfour
      \ifNPEEOpeningPage
        \renewcommand{\NPEEPageCount}{8}%
      \else
        \renewcommand{\NPEEPageCount}{7}%
      \fi
    \else
      \ifNPEEOpeningPage
        \renewcommand{\NPEEPageCount}{8}%
      \else
        \renewcommand{\NPEEPageCount}{7}%
      \fi
    \fi
  \fi}
\NPEEUpdateDefaultPageCount

\newcommand{\NPEESetPageCount}[1]{%
  \NPEEPageCountAutomaticfalse
  \renewcommand{\NPEEPageCount}{#1}}
\newcommand{\NPEEUseAutomaticPageCount}{%
  \NPEEPageCountAutomatictrue
  \NPEEUpdateDefaultPageCount}

\NPEEDeclareSetupKeys{
  paper/page-count/.code={\NPEESetPageCount{#1}}
}

\newcommand{\NPEEStorePaperPageCount}[2]{%
  \expandafter\gdef\csname NPEEStoredPageCount@#1\endcsname{#2}}
\newcommand{\NPEEWritePaperPageCount}[2]{%
  \begingroup
    \immediate\write\@auxout{\string\NPEEStorePaperPageCount{#1}{#2}}%
  \endgroup}
\newcommand{\NPEELoadPaperPageCount}[1]{%
  \ifNPEEPageCountAutomatic
    \ifcsname NPEEStoredPageCount@#1\endcsname
      \edef\NPEEPageCount{\csname NPEEStoredPageCount@#1\endcsname}%
    \else
      \NPEEUpdateDefaultPageCount
      \fi
  \fi}

% Compact collections keep a short paper physically usable when it would
% otherwise produce a fragmentary handout.  A3 keeps four logical pages (two
% landscape sheets), while ordinary A4 keeps three so an unused fourth sheet is
% not manufactured at the end of a short paper.  The explicit a4-blank target
% raises the A4 floor to four sheets for print workflows that need a stable
% four-page handout.
% Blank sheets remain part of the paper lifecycle, so their footer and
% watermark are consistent with the learned final page total.
\newcommand{\NPEEEnsureCompactMinimumPages}{%
  \ifNPEECompact
    \ifNPEEAfourBlank
      \def\NPEEMinimumLogicalPages{4}%
    \else
      \ifNPEEAfour
        \def\NPEEMinimumLogicalPages{3}%
      \else
        \def\NPEEMinimumLogicalPages{4}%
      \fi
    \fi
    \count@=\value{npeelogicalpage}\relax
    \advance\count@ by -1\relax
    \ifnum\count@<\NPEEMinimumLogicalPages
      \ifNPEEPageCountAutomatic
        \edef\NPEEPageCount{\NPEEMinimumLogicalPages}%
      \fi
      \loop
        \null\clearpage
        \count@=\value{npeelogicalpage}\relax
        \advance\count@ by -1\relax
        \ifnum\count@<\NPEEMinimumLogicalPages
      \repeat
    \fi
  \fi}

% Called after the final body sheet has been shipped.  The logical counter is
% maintained by the active page renderer (currently the footer module).
\newcommand{\NPEEFinalizeActivePaper}{%
  \ifNPEEExamActive
    \count@=\value{npeelogicalpage}\relax
    \advance\count@ by -1\relax
    \ifnum\count@<1 \count@=1\fi
    \edef\NPEEFinalPaperPageCount{\number\count@}%
    \NPEEEnsureCompactMinimumPages
    \count@=\value{npeelogicalpage}\relax
    \advance\count@ by -1\relax
    \ifnum\count@<1 \count@=1\fi
    \edef\NPEEFinalPaperPageCount{\number\count@}%
    \ifNPEEPageCountAutomatic
      \ifcsname NPEEStoredPageCount@\arabic{npeeexampaper}\endcsname
        \edef\NPEEOldPaperPageCount{\csname NPEEStoredPageCount@\arabic{npeeexampaper}\endcsname}%
        \ifnum\NPEEOldPaperPageCount=\NPEEFinalPaperPageCount\else
          \NPEEWarningNoLine{npee-math-exam}{Paper \arabic{npeeexampaper} page total changed to \NPEEFinalPaperPageCount; rerun XeLaTeX}%
        \fi
      \fi
      \NPEEWritePaperPageCount{\arabic{npeeexampaper}}{\NPEEFinalPaperPageCount}%
    \fi
  \fi}




% -----------------------------------------------------------------------------
% Feature section: paper lifecycle
% -----------------------------------------------------------------------------

% This package owns only transitions between book matter and examination
% matter.  Optional capabilities (watermark, security, footer, candidate
% panel, and paper metadata) subscribe through hooks instead of being called
% from the lifecycle implementation.

\newcommand{\NPEEApplyExamPagePalette}{%
  \ifNPEEEyecare
    \pagecolor{NPEEEyePage}\color{NPEEEyeText}%
  \else
    \pagecolor{white}\color{black}%
  \fi}

% Notify optional capabilities without requiring any of their implementation
% packages.  This is also the public escape hatch for a downstream renderer
% that wants to suspend overlays before entering an appendix.
\newcommand{\NPEEDeactivateExamFeatures}{%
  \UseHook{npee-exam/transition}}

\newcommand{\NPEEBeginBookBody}{%
  \NPEEApplyExamPagePalette
  \setcounter{page}{1}%
  \setcounter{npeeexampaper}{0}%
  \setcounter{npeelogicalpage}{1}%
  \NPEEExamWatermarkfalse
  \global\NPEEConfidentialMarkPendingfalse
  \global\NPEEConfidentialMarkActivefalse
  \NPEEExamSpreadfalse
  \NPEEExamActivefalse
  \NPEEExamFooterfalse
  \UseHook{npee-exam/book-body/begin}%
  \pagestyle{empty}}

\newcommand{\NPEEExamPaperStart}{%
  \UseHook{npee-exam/paper/before-start}%
  \NPEEExamEndColumns
  \clearpage
  % The previous paper is complete only after its final balanced columns have
  % shipped.  The hook lets optional modules release their per-paper state.
  \NPEEFinalizeActivePaper
  \ifNPEEExamActive\UseHook{npee-exam/paper/end}\fi
  \NPEEApplyExamPagePalette
  \NPEEUpdateOpeningPageState
  \NPEEUpdateDefaultPageCount
  \refstepcounter{npeeexampaper}%
  \NPEELoadPaperPageCount{\arabic{npeeexampaper}}%
  \setcounter{npeetotalpoints}{0}%
  \setcounter{npeelogicalpage}{1}%
  \NPEEExamActivetrue
  \ifNPEEAfour\NPEEExamSpreadfalse\else\NPEEExamSpreadtrue\fi
  \UseHook{npee-exam/paper/start}%
  \thispagestyle{empty}%
  \UseHook{npee-exam/paper/bookmark}%
  \NPEEExamBeginColumns
  \UseHook{npee-exam/paper/opening}}

\newcommand{\NPEEExamPaperEnd}{%
  \NPEEExamEndColumns
  % A paper may already have been closed by \NPEEBackMatterStart before the
  % source reaches this compatibility terminator.  In that case an
  % unconditional \clearpage would manufacture a blank trailing page (most
  % visible when the source-mapping table occupies more than one page).
  \ifNPEEExamActive
    \clearpage
    \NPEEFinalizeActivePaper
    \UseHook{npee-exam/paper/end}%
  \fi
  \NPEEExamWatermarkfalse
  \global\NPEEConfidentialMarkPendingfalse
  \global\NPEEConfidentialMarkActivefalse
  \NPEEExamActivefalse
  \NPEEExamFooterfalse}

% Standalone users may end after one paper.  Collection builds normally close
% the paper at the next start or at an appendix transition.
\AtEndDocument{%
  \NPEEExamEndColumns
  \ifNPEEExamActive
    \clearpage
    \NPEEFinalizeActivePaper
    \UseHook{npee-exam/paper/end}%
    \global\NPEEExamActivefalse
  \fi}

\newcommand{\NPEEBeginAppendix}[2]{%
  \NPEEExamEndColumns
  \clearpage
  \NPEEFinalizeActivePaper
  \NPEEDeactivateExamFeatures
  \global\NPEEExamSpreadfalse
  \global\NPEEExamWatermarkfalse
  \global\NPEEConfidentialMarkPendingfalse
  \global\NPEEConfidentialMarkActivefalse
  \global\NPEEExamActivefalse
  \global\NPEEExamFooterfalse
  \pagecolor{white}\color{black}%
  \pagestyle{empty}%
  \NPEEBookmark{#1}{#2}}

\newcommand{\NPEEBackMatterStart}[1]{%
  \NPEEExamEndColumns
  \clearpage
  \NPEEFinalizeActivePaper
  \NPEEDeactivateExamFeatures
  \global\NPEEExamSpreadfalse
  \global\NPEEExamWatermarkfalse
  \global\NPEEConfidentialMarkPendingfalse
  \global\NPEEConfidentialMarkActivefalse
  \global\NPEEExamActivefalse
  \global\NPEEExamFooterfalse
  \pagecolor{white}\color{black}%
  \pagestyle{empty}%
  \NPEEBookmark{#1}{backmatter}}




% -----------------------------------------------------------------------------
% Feature section: watermark
% -----------------------------------------------------------------------------

% Watermark rendering is an optional shipout capability.  It owns only the
% watermark token, geometry and hook; publication-specific text is supplied
% by the selected document profile.
%
% graphicx is required explicitly rather than only as a transitive TikZ
% dependency.  This keeps the figure API usable when a downstream profile
% replaces or omits the watermark renderer.
\RequirePackage{graphicx}
\RequirePackage{tikz}
\RequirePackage{tikz-3dplot}
\usetikzlibrary{patterns}

% Figures are kept in their own paragraph so a wide TikZ box cannot inherit the
% question stem's line width.  Oversized diagrams are reduced only when needed;
% ordinary diagrams retain their source scale and are horizontally centred.
\newsavebox{\NPEETikzFigureBox}
\newcommand{\NPEEIncludeTikz}[1]{%
  \par\addvspace{1mm}\noindent
  \begingroup
    \sbox{\NPEETikzFigureBox}{#1}%
    \ifdim\wd\NPEETikzFigureBox>\linewidth
      \makebox[\linewidth][c]{\resizebox{\linewidth}{!}{#1}}%
    \else
      \makebox[\linewidth][c]{#1}%
    \fi
  \endgroup
  \par\addvspace{1mm}}
\newcommand{\NPEEChoiceGraphic}[1]{%
  \par\vspace{.35mm}\noindent
  \sbox{\NPEETikzFigureBox}{#1}%
  \ifdim\wd\NPEETikzFigureBox>\linewidth
    \makebox[\linewidth][c]{\resizebox{\linewidth}{!}{#1}}%
  \else
    \makebox[\linewidth][c]{#1}%
  \fi
  \par}

\newcommand{\NPEEWatermarkText}{}
\newcommand{\NPEEWatermarkAngle}{24}
\newcommand{\NPEEWatermarkOpacity}{.060}
\newcommand{\NPEEWatermarkInkPercent}{12}
\newcommand{\NPEEWatermarkFontSize}{24pt}
\newcommand{\NPEEWatermarkColor}{black}
\newcommand{\NPEEWatermarkTextColor}{black}
\newcommand{\NPEEWatermarkBackgroundColor}{white}
\newcommand{\NPEEWatermarkColorOpacity}{0}
\newcommand{\NPEEWatermarkTextColorOpacity}{.060}
\newcommand{\NPEEWatermarkBackgroundColorOpacity}{0}
\newcommand{\NPEESetWatermarkText}[1]{\renewcommand{\NPEEWatermarkText}{#1}}
\newcommand{\NPEESetWatermarkAngle}[1]{\renewcommand{\NPEEWatermarkAngle}{#1}}
\newcommand{\NPEEUpdateWatermarkInkPercent}{%
  \pgfmathparse{max(0,min(100,100*(\NPEEWatermarkOpacity)))}%
  \xdef\NPEEWatermarkInkPercent{\pgfmathresult}}
\newcommand{\NPEESetWatermarkOpacity}[1]{%
  \renewcommand{\NPEEWatermarkOpacity}{#1}%
  \renewcommand{\NPEEWatermarkTextColorOpacity}{#1}%
  \NPEEUpdateWatermarkInkPercent}
\NPEEUpdateWatermarkInkPercent
\newcommand{\NPEESetWatermarkFontSize}[1]{\renewcommand{\NPEEWatermarkFontSize}{#1}}
\newcommand{\NPEESetWatermarkColor}[1]{\renewcommand{\NPEEWatermarkColor}{#1}}
\newcommand{\NPEESetWatermarkTextColor}[1]{\renewcommand{\NPEEWatermarkTextColor}{#1}}
\newcommand{\NPEESetWatermarkBackgroundColor}[1]{\renewcommand{\NPEEWatermarkBackgroundColor}{#1}}
\newcommand{\NPEESetWatermarkColorOpacity}[1]{\renewcommand{\NPEEWatermarkColorOpacity}{#1}}
\newcommand{\NPEESetWatermarkTextColorOpacity}[1]{\renewcommand{\NPEEWatermarkTextColorOpacity}{#1}}
\newcommand{\NPEESetWatermarkBackgroundColorOpacity}[1]{\renewcommand{\NPEEWatermarkBackgroundColorOpacity}{#1}}
\newcommand{\NPEEEnableWatermark}{\NPEEWatermarkEnabledtrue}
\newcommand{\NPEEDisableWatermark}{\NPEEWatermarkEnabledfalse}

% Watermark activation is a paper concern, but its implementation is local to
% this package.  The hook samples the option at paper start and clears it for
% every non-examination transition.
\AddToHook{npee-exam/book-body/begin}{\global\NPEEExamWatermarkfalse}
\AddToHook{npee-exam/paper/start}{%
  \ifNPEEWatermarkEnabled
    \global\NPEEExamWatermarktrue
  \else
    \global\NPEEExamWatermarkfalse
  \fi}
\AddToHook{npee-exam/paper/end}{\global\NPEEExamWatermarkfalse}
\AddToHook{npee-exam/transition}{\global\NPEEExamWatermarkfalse}

\newcommand{\NPEEExamWatermarkMark}[2]{%
  \node[anchor=center,inner sep=0pt,rotate=\NPEEWatermarkAngle,
    draw=none,
    draw opacity=\NPEEWatermarkColorOpacity,
    fill=none,
    fill opacity=\NPEEWatermarkBackgroundColorOpacity,
    text=\NPEEWatermarkTextColor,
    text opacity=\NPEEWatermarkTextColorOpacity,
    font=\rmfamily\itshape\mdseries\fontsize{\NPEEWatermarkFontSize}{\NPEEWatermarkFontSize}\selectfont]
    at ([xshift=#1,yshift=-#2]current page.north west) {\NPEEWatermarkText};}

% The default positions reproduce the reference sheets.  They are exposed as
% macros so a publisher can use a different watermark grid without editing
% the shipout hook.
\newcommand{\NPEEWatermarkMarksAfour}{%
  \NPEEExamWatermarkMark{48mm}{55mm}%
  \NPEEExamWatermarkMark{105mm}{130mm}%
  \NPEEExamWatermarkMark{162mm}{205mm}}
\newcommand{\NPEEWatermarkMarksAthree}{%
  \NPEEExamWatermarkMark{60mm}{60mm}%
  \NPEEExamWatermarkMark{105mm}{148mm}%
  \NPEEExamWatermarkMark{150mm}{236mm}%
  \NPEEExamWatermarkMark{270mm}{60mm}%
  \NPEEExamWatermarkMark{315mm}{148mm}%
  \NPEEExamWatermarkMark{360mm}{236mm}}
\newcommand{\NPEEWatermarkMarksSpread}{%
  \NPEEExamWatermarkMark{53.65mm}{52.57mm}%
  \NPEEExamWatermarkMark{93.13mm}{128.94mm}%
  \NPEEExamWatermarkMark{132.61mm}{205.31mm}%
  \NPEEExamWatermarkMark{239.92mm}{52.57mm}%
  \NPEEExamWatermarkMark{279.40mm}{128.94mm}%
  \NPEEExamWatermarkMark{318.88mm}{205.31mm}}
\newcommand{\NPEESetWatermarkMarksAfour}[1]{\renewcommand{\NPEEWatermarkMarksAfour}{#1}}
\newcommand{\NPEESetWatermarkMarksAthree}[1]{\renewcommand{\NPEEWatermarkMarksAthree}{#1}}
\newcommand{\NPEESetWatermarkMarksSpread}[1]{\renewcommand{\NPEEWatermarkMarksSpread}{#1}}

\NPEEDeclareSetupKeys{
  watermark/show/.is if=NPEEWatermarkEnabled,
  watermark/text/.code={\NPEESetWatermarkText{#1}},
  watermark/angle/.code={\NPEESetWatermarkAngle{#1}},
  watermark/opacity/.code={\NPEESetWatermarkOpacity{#1}},
  watermark/font-size/.code={\NPEESetWatermarkFontSize{#1}},
  watermark/color/.code={\NPEESetWatermarkColor{#1}},
  watermark/text-color/.code={\NPEESetWatermarkTextColor{#1}},
  watermark/background-color/.code={\NPEESetWatermarkBackgroundColor{#1}}
}

\AddToHook{shipout/background}{%
  \ifNPEEExamWatermark
    \begin{tikzpicture}[remember picture,overlay]
      \ifNPEEAthree
        \NPEEWatermarkMarksAthree
      \else\ifNPEEAfour
        \NPEEWatermarkMarksAfour
      \else
        \NPEEWatermarkMarksSpread
      \fi\fi
    \end{tikzpicture}%
  \fi}




% -----------------------------------------------------------------------------
% Feature section: footer anchor
% -----------------------------------------------------------------------------

% Footer placement consumes the independent pagination capability.  Visible
% ornament and wording remain replaceable document-level formatters.
\newcommand{\NPEEFormatPaperLabel}[1]{第#1套}
\newcommand{\NPEEFormatFooterPage}[2]{第 #1 页（共 #2 页）}
\newcommand{\NPEEExamPaperLabel}{%
  \ifx\NPEECurrentPaperHeading\@empty
    \NPEEFormatPaperLabel{\NPEEFormatPaperNumber}%
  \else
    \NPEECurrentPaperHeading
  \fi}
% The footer is intentionally subordinate to the body text and is drawn as an
% overlay, so its size does not alter question flow.
\newcommand{\NPEEFooterFontSize}{11pt}
\newcommand{\NPEEFooterLineHeight}{13.5pt}
\newcommand{\NPEEFooterOffset}{24mm}
\newcommand{\NPEESetFooterStyle}[2]{%
  \renewcommand{\NPEEFooterFontSize}{#1}%
  \renewcommand{\NPEEFooterLineHeight}{#2}}
\newcommand{\NPEESetFooterOffset}[1]{\renewcommand{\NPEEFooterOffset}{#1}}
\NPEEDeclareSetupKeys{
  footer/font-size/.code={\renewcommand{\NPEEFooterFontSize}{#1}},
  footer/line-height/.code={\renewcommand{\NPEEFooterLineHeight}{#1}},
  footer/offset/.code={\NPEESetFooterOffset{#1}}
}
% The class supplies footer data and placement only.  Projects may replace
% this formatter to add publication-specific wording or vector artwork.
\newcommand{\NPEEFormatFooterContent}[3]{%
  #1\quad\NPEEFormatFooterPage{#2}{#3}}
\newcommand{\ExamFormatFooterContent}[3]{%
  \NPEEFormatFooterContent{#1}{#2}{#3}}
\newcommand{\NPEELogicalFooter}[2]{%
  \node[anchor=south,inner sep=0pt,text=black,font=\NPEEBodyFace\fontsize{\NPEEFooterFontSize}{\NPEEFooterLineHeight}\selectfont]
    at ([xshift=#1,yshift=\NPEEFooterOffset]current page.south west)
    {\ExamFormatFooterContent{\NPEEExamPaperLabel}{#2}{\NPEEPageCount}};}
\newcommand{\NPEEDrawExamSpread}{%
  \begin{tikzpicture}[remember picture,overlay]
    \NPEELogicalFooter{.25\paperwidth}{\arabic{npeelogicalpage}}%
    \NPEELogicalFooter{.75\paperwidth}{\number\numexpr\value{npeelogicalpage}+1\relax}%
  \end{tikzpicture}}
\newcommand{\NPEEDrawExamPage}{%
  \begin{tikzpicture}[remember picture,overlay]
    \NPEELogicalFooter{.5\paperwidth}{\arabic{npeelogicalpage}}%
  \end{tikzpicture}}

% The lifecycle does not know that a footer exists.  Registering these small
% state transitions keeps the renderer optional and makes appendix pages
% automatically free of examination footers.
\AddToHook{npee-exam/book-body/begin}{\global\NPEEExamFooterfalse}
\AddToHook{npee-exam/paper/start}{\global\NPEEExamFootertrue}
\AddToHook{npee-exam/paper/end}{\global\NPEEExamFooterfalse}
\AddToHook{npee-exam/transition}{\global\NPEEExamFooterfalse}

\AddToHook{shipout/foreground}{%
  \ifNPEEExamFooter
    \ifNPEEExamSpread\NPEEDrawExamSpread\else\NPEEDrawExamPage\fi
    \ifNPEEExamSpread\NPEEDrawExamDivider\fi
  \fi}
\AddToHook{shipout/after}{%
  \ifNPEEExamFooter
    \ifNPEEExamSpread\addtocounter{npeelogicalpage}{2}\else\addtocounter{npeelogicalpage}{1}\fi
  \fi}




% -----------------------------------------------------------------------------
% Feature section: security mark
% -----------------------------------------------------------------------------

% The security mark is a zero-height opening-sheet overlay.  Its visible
% wording is deliberately a document-level token; this package only supplies
% level mapping, state sampling and placement.  The star is Unicode text so
% the mark remains searchable and does not introduce a Dingbats dependency.
\newfontfamily\NPEESecurityStarFace{Arial Unicode MS}
\newcommand{\NPEESecurityStar}{{\NPEESecurityStarFace ★}}

\newcommand{\NPEEConfidentialMarkText}{}
\newcommand{\NPEEConfidentialMarkActiveText}{}
\newcommand{\NPEESecurityLevel}{3}

\newcommand{\NPEESecurityActivationText}{启用前}

\newcommand{\NPEESecurityLevelOneText}{秘密}

\newcommand{\NPEESecurityLevelTwoText}{机密}

\newcommand{\NPEESecurityLevelThreeText}{绝密}
% The opening mark follows the compact black top-left treatment used on
% formal Chinese examination papers.  Keep the wording configurable, but do
% not insert decorative inter-word gaps: the requested default is the single
% tight label ``启用前★绝密``.
\newcommand{\NPEESecuritySeparator}{}
\newcommand{\NPEEConfidentialMarkFontSize}{11.5bp}
\newcommand{\NPEEConfidentialMarkLineHeight}{14bp}
\newcommand{\NPEEConfidentialMarkAfourX}{16mm}
\newcommand{\NPEEConfidentialMarkAfourY}{14mm}
\newcommand{\NPEEConfidentialMarkSpreadX}{20mm}
\newcommand{\NPEEConfidentialMarkSpreadY}{10mm}
\newcommand{\NPEEConfidentialMarkAthreeX}{24mm}
\newcommand{\NPEEConfidentialMarkAthreeY}{12mm}

% State-secret grades used by Chinese examination conventions.  Level 0 is
% deliberately the disabled state; it is not a legal classification label.
\newcommand{\NPEESecurityLevelName}[1]{%
  \ifnum\pdfstrcmp{#1}{1}=0 \NPEESecurityLevelOneText%
  \else\ifnum\pdfstrcmp{#1}{2}=0 \NPEESecurityLevelTwoText%
  \else\ifnum\pdfstrcmp{#1}{3}=0 \NPEESecurityLevelThreeText%
  \else\ifnum\pdfstrcmp{#1}{0}=0 %
  \else\ifnum\pdfstrcmp{#1}{custom}=0 %
  \else
    \NPEEWarning{npee-math-exam}{Unknown security level `#1'}%
  \fi\fi\fi\fi\fi}
\newcommand{\NPEERebuildSecurityText}{%
  \renewcommand{\NPEEConfidentialMarkText}{%
    % Keep the user-facing order ``启用前★绝密`` and make the mark visually
    % compact, as on formal examination stock.
    \ifx\NPEESecurityActivationText\@empty\else
      \NPEESecurityActivationText
    \fi
    \NPEESecurityStar
    \NPEESecuritySeparator
    \NPEESecurityLevelName{\NPEESecurityLevel}}}
\newcommand{\NPEESetSecurityActivationText}[1]{%
  \renewcommand{\NPEESecurityActivationText}{#1}%
  \ifNPEESecurityCustomText\else
    \ifnum\pdfstrcmp{\NPEESecurityLevel}{0}=0\else
      \NPEERebuildSecurityText
    \fi
  \fi}
\newcommand{\NPEESetSecurityText}[1]{%
  \if\relax\detokenize{#1}\relax
    \NPEEWarning{npee-math-exam}{Empty security text ignored}%
  \else
    \renewcommand{\NPEESecurityLevel}{custom}%
    \NPEESecurityCustomTexttrue
    \renewcommand{\NPEEConfidentialMarkText}{#1}%
  \fi}
\newcommand{\NPEESetSecurityLevel}[1]{%
  \NPEENormalizeValue{#1}%
  \edef\NPEETempSecurityLevel{\NPEENormalizedValue}%
  \if\relax\detokenize\expandafter{\NPEETempSecurityLevel}\relax
    \NPEEWarning{npee-math-exam}{Empty security level ignored}%
  \else\ifnum\pdfstrcmp{\NPEETempSecurityLevel}{0}=0
    \renewcommand{\NPEESecurityLevel}{0}%
    \NPEESecurityCustomTextfalse
    \renewcommand{\NPEEConfidentialMarkText}{}%
    \NPEEDisableConfidentialMark
  \else\ifnum\pdfstrcmp{\NPEETempSecurityLevel}{1}=0
    \renewcommand{\NPEESecurityLevel}{1}%
    \NPEESecurityCustomTextfalse
    \NPEERebuildSecurityText
    \NPEEEnableConfidentialMark
  \else\ifnum\pdfstrcmp{\NPEETempSecurityLevel}{2}=0
    \renewcommand{\NPEESecurityLevel}{2}%
    \NPEESecurityCustomTextfalse
    \NPEERebuildSecurityText
    \NPEEEnableConfidentialMark
  \else\ifnum\pdfstrcmp{\NPEETempSecurityLevel}{3}=0
    \renewcommand{\NPEESecurityLevel}{3}%
    \NPEESecurityCustomTextfalse
    \NPEERebuildSecurityText
    \NPEEEnableConfidentialMark
  \else\ifnum\pdfstrcmp{\NPEETempSecurityLevel}{custom}=0
    \ifNPEESecurityCustomText
      \renewcommand{\NPEESecurityLevel}{custom}%
      \NPEEEnableConfidentialMark
    \else
      \NPEEWarning{npee-math-exam}{Security level `custom' requires security text}%
    \fi
  \else
    \NPEEWarning{npee-math-exam}{Unknown security level `\NPEETempSecurityLevel'; expected 0, 1, 2, 3, or custom}%
  \fi\fi\fi\fi\fi\fi}

% Historical one-argument setter: arbitrary content remains supported and does
% not change the legacy visibility switch.
\newcommand{\NPEESetConfidentialMark}[1]{\NPEESetSecurityText{#1}}
\newcommand{\NPEESetConfidentialMarkStyle}[2]{%
  \renewcommand{\NPEEConfidentialMarkFontSize}{#1}%
  \renewcommand{\NPEEConfidentialMarkLineHeight}{#2}}
\newcommand{\NPEEEnableConfidentialMark}{\NPEEConfidentialMarkEnabledtrue}

\newcommand{\NPEEDisableConfidentialMark}{\NPEEConfidentialMarkEnabledfalse}
\NPEESetSecurityLevel{3}
\newcommand{\NPEEArmConfidentialMark}{%
  % Freeze the text at paper start.  Later configuration affects the next
  % paper, never the already armed opening sheet.
  \begingroup
    \protected@edef\NPEETempActiveSecurityText{\NPEEConfidentialMarkText}%
    \global\let\NPEEConfidentialMarkActiveText\NPEETempActiveSecurityText
  \endgroup
  \ifNPEEConfidentialMarkEnabled
    \ifnum\pdfstrcmp{\NPEESecurityLevel}{0}=0
      \global\NPEEConfidentialMarkActivefalse
    \else
      \global\NPEEConfidentialMarkActivetrue
    \fi
  \else
    \global\NPEEConfidentialMarkActivefalse
  \fi
  \ifNPEEConfidentialMarkActive
    \global\NPEEConfidentialMarkPendingtrue
  \else
    \global\NPEEConfidentialMarkPendingfalse
  \fi}
\newcommand{\NPEEDisarmConfidentialMark}{%
  \global\NPEEConfidentialMarkPendingfalse
  \global\NPEEConfidentialMarkActivefalse}

\NPEEDeclareSetupKeys{
  security/show/.is if=NPEEConfidentialMarkEnabled,
  security/level/.code={\NPEESetSecurityLevel{#1}},
  security/text/.code={\NPEESetSecurityText{#1}},
  security/suffix/.code={\NPEESetSecurityActivationText{#1}},
  security/font-size/.code={\renewcommand{\NPEEConfidentialMarkFontSize}{#1}},
  security/line-height/.code={\renewcommand{\NPEEConfidentialMarkLineHeight}{#1}},
  security/a4-x/.code={\renewcommand{\NPEEConfidentialMarkAfourX}{#1}},
  security/a4-y/.code={\renewcommand{\NPEEConfidentialMarkAfourY}{#1}},
  security/a3-x/.code={\renewcommand{\NPEEConfidentialMarkAthreeX}{#1}},
  security/a3-y/.code={\renewcommand{\NPEEConfidentialMarkAthreeY}{#1}},
  security/spread-x/.code={\renewcommand{\NPEEConfidentialMarkSpreadX}{#1}},
  security/spread-y/.code={\renewcommand{\NPEEConfidentialMarkSpreadY}{#1}},
  confidential/show/.is if=NPEEConfidentialMarkEnabled,
  confidential/level/.code={\NPEESetSecurityLevel{#1}},
  confidential/text/.code={\NPEESetSecurityText{#1}},
  confidential/suffix/.code={\NPEESetSecurityActivationText{#1}},
  confidential/font-size/.code={\renewcommand{\NPEEConfidentialMarkFontSize}{#1}},
  confidential/line-height/.code={\renewcommand{\NPEEConfidentialMarkLineHeight}{#1}},
  confidential/a4-x/.code={\renewcommand{\NPEEConfidentialMarkAfourX}{#1}},
  confidential/a4-y/.code={\renewcommand{\NPEEConfidentialMarkAfourY}{#1}},
  confidential/a3-x/.code={\renewcommand{\NPEEConfidentialMarkAthreeX}{#1}},
  confidential/a3-y/.code={\renewcommand{\NPEEConfidentialMarkAthreeY}{#1}},
  confidential/spread-x/.code={\renewcommand{\NPEEConfidentialMarkSpreadX}{#1}},
  confidential/spread-y/.code={\renewcommand{\NPEEConfidentialMarkSpreadY}{#1}}
}
\newcommand{\NPEEDrawConfidentialMark}{%
  \begin{tikzpicture}[remember picture,overlay]
    \ifNPEEAthree
      \node[anchor=north west,inner sep=0pt,text=black,
        font=\NPEEHeadingFace
          \fontsize{\NPEEConfidentialMarkFontSize}{\NPEEConfidentialMarkLineHeight}\selectfont]
        at ([xshift=\NPEEConfidentialMarkAthreeX,yshift=-\NPEEConfidentialMarkAthreeY]current page.north west)
        {\NPEEConfidentialMarkActiveText};%
    \else\ifNPEEAfour
      \node[anchor=north west,inner sep=0pt,text=black,
        font=\NPEEHeadingFace
          \fontsize{\NPEEConfidentialMarkFontSize}{\NPEEConfidentialMarkLineHeight}\selectfont]
        at ([xshift=\NPEEConfidentialMarkAfourX,yshift=-\NPEEConfidentialMarkAfourY]current page.north west)
        {\NPEEConfidentialMarkActiveText};%
    \else
      \node[anchor=north west,inner sep=0pt,text=black,
        font=\NPEEHeadingFace
          \fontsize{\NPEEConfidentialMarkFontSize}{\NPEEConfidentialMarkLineHeight}\selectfont]
        at ([xshift=\NPEEConfidentialMarkSpreadX,yshift=-\NPEEConfidentialMarkSpreadY]current page.north west)
        {\NPEEConfidentialMarkActiveText};%
    \fi\fi
  \end{tikzpicture}}

% Security is a one-sheet opening capability.  Its lifecycle state is
% registered here so the paper coordinator remains independent of TikZ and
% the numeric level mapping.
\AddToHook{npee-exam/book-body/begin}{\NPEEDisarmConfidentialMark}
\AddToHook{npee-exam/paper/start}{\NPEEArmConfidentialMark}
\AddToHook{npee-exam/paper/end}{\NPEEDisarmConfidentialMark}
\AddToHook{npee-exam/transition}{\NPEEDisarmConfidentialMark}

% The paper lifecycle samples the text at paper start and arms this flag for
% exactly one physical sheet.  Keeping the hook here makes the capability
% usable by a different lifecycle driver as well.
\AddToHook{shipout/foreground}{%
  \ifNPEEConfidentialMarkPending
    \ifNPEEConfidentialMarkActive
      \NPEEDrawConfidentialMark
    \fi
  \fi}
\AddToHook{shipout/after}{%
  \ifNPEEConfidentialMarkPending
    \global\NPEEConfidentialMarkPendingfalse
  \fi}




% -----------------------------------------------------------------------------
% Feature section: publication metadata slots
% -----------------------------------------------------------------------------

% These are empty, document-scoped extension points rather than publication
% content.  A project entry point supplies the values after \documentclass;
% the reusable engine never chooses a subject, collection, publisher, or title.
\providecommand{\NPEESubjectName}{}
\providecommand{\NPEESubjectCode}{}
\providecommand{\NPEESubjectKey}{}
\providecommand{\NPEECollectionKey}{}
\providecommand{\NPEECollectionName}{}
\providecommand{\NPEECollectionCount}{}
\providecommand{\NPEECollectionTitle}{}
% Optional document-level visible paper label. Concrete projects define it.
\providecommand{\NPEEExamSetLabel}{第一套}




% -----------------------------------------------------------------------------
% Feature section: paper metadata
% -----------------------------------------------------------------------------


\newcommand{\NPEEFormatPaperBookmark}[1]{第#1套}
\newcommand{\NPEEPaperHeadingTitle}{}
\newcommand{\NPEECurrentPaperHeading}{}
% One-shot metadata for the next paper.  Empty title delegates to the
% document-level formatter; the class-owned destination counter keeps
% otherwise identical bookmark keys unique.
\newif\ifNPEEPaperBookmarkEnabled
\NPEEPaperBookmarkEnabledtrue
\newcommand{\NPEEPaperBookmarkTitle}{}
\newcommand{\NPEEPaperBookmarkKey}{paper}
\NPEEDeclareSetupKeys{
  paper/bookmark/.code={%
    \NPEEWarningNoLine{npee-math-exam}{Paper PDF bookmarks are mandatory; paper/bookmark is ignored}},
  paper/bookmark-title/.code={%
    \renewcommand{\NPEEPaperBookmarkTitle}{#1}},
  paper/bookmark-key/.code={%
    \renewcommand{\NPEEPaperBookmarkKey}{#1}},
  paper/heading-title/.code={%
    \renewcommand{\NPEEPaperHeadingTitle}{#1}}
}
\newcommand{\NPEEResetPaperInfo}{%
  \NPEEPaperBookmarkEnabledtrue
  \renewcommand{\NPEEPaperBookmarkTitle}{}%
  \renewcommand{\NPEEPaperBookmarkKey}{paper}%
  \renewcommand{\NPEEPaperHeadingTitle}{}%
}
\newcommand{\NPEESetPaperInfo}[1]{%
  \if\relax\detokenize{#1}\relax\else
    \pgfkeys{/npee/paper/.cd,#1}%
  \fi}
\newcommand{\NPEEWritePaperBookmark}{%
  \def\NPEECurrentPaperBookmarkTitle{}%
  \ifx\NPEEPaperBookmarkTitle\@empty
    \edef\NPEECurrentPaperBookmarkTitle{\NPEEFormatPaperBookmark{\arabic{npeeexampaper}}}%
  \else
    \edef\NPEECurrentPaperBookmarkTitle{\NPEEPaperBookmarkTitle}%
  \fi
  \ifx\NPEEPaperHeadingTitle\@empty
    \edef\NPEECurrentPaperHeading{\NPEECurrentPaperBookmarkTitle}%
  \else
    \edef\NPEECurrentPaperHeading{\NPEEPaperHeadingTitle}%
  \fi
  \NPEEBookmarkAtLevel{1}{\NPEECurrentPaperBookmarkTitle}{\NPEEPaperBookmarkKey}%
  \ifNPEECollectionContentsEnabled
    \ifNPEECollectionPaperContentsEnabled
       \NPEEAddContentsEntry{subsection}{\NPEECurrentPaperBookmarkTitle}%
    \fi
  \fi
  \NPEEResetPaperInfo}
\AddToHook{npee-exam/paper/bookmark}{\NPEEWritePaperBookmark}




% -----------------------------------------------------------------------------
% Feature section: candidate information
% -----------------------------------------------------------------------------

\RequirePackage{array}

\newcommand{\NPEECandidateNotice}[2]{%
  \par\begingroup
  \leftskip=0pt
  \hangindent=4.0mm\hangafter=1
  \noindent\textup{#1.}\enspace #2\par
  \endgroup\vspace{.45mm}}
\newlength{\NPEECandidateLabelWidth}
\newlength{\NPEECandidateDigitWidth}
\setlength{\NPEECandidateLabelWidth}{31.5mm}
\newlength{\NPEECandidateRowHeight}
\setlength{\NPEECandidateRowHeight}{9.3mm}
\newcommand{\NPEECandidateAfourRowHeight}{9.3mm}
% Separate row heights are useful for forms whose candidate-number boxes need
% more writing room than the name row.  They are generic layout parameters,
% not publication content, and default to the same height for compatibility.
\newlength{\NPEECandidateNumberRowHeight}
\setlength{\NPEECandidateNumberRowHeight}{9.3mm}
\newlength{\NPEECandidateNameRowHeight}
\setlength{\NPEECandidateNameRowHeight}{9.3mm}
\newcommand{\NPEECandidateAfourNumberRowHeight}{\NPEECandidateAfourRowHeight}
\newcommand{\NPEECandidateAfourNameRowHeight}{\NPEECandidateAfourRowHeight}
\newlength{\NPEECandidateCellInset}
\setlength{\NPEECandidateCellInset}{.8mm}
\newcommand{\NPEECandidateLabelFace}{\NPEEBodyFace\fontsize{10.5pt}{13pt}\selectfont}
% The label cells in the candidate-information grid use the same explicit
% height as the row.  Keeping this as a small reusable primitive avoids
% relying on an empty tabular cell to establish the row height and makes the
% table stable when a document supplies a longer custom label.
\newcommand{\NPEECandidateCell}[1]{%
  % Use a real fixed-height box so both labels are centred horizontally and
  % vertically even when a document supplies a longer custom label.
  \parbox[c][\NPEECandidateRowHeight][c]{\dimexpr\linewidth-2\NPEECandidateCellInset\relax}{%
    \centering\NPEECandidateLabelFace #1\strut}}
\newcommand{\NPEECandidateCellWithHeight}[2]{%
  \parbox[c][#1][c]{\dimexpr\linewidth-2\NPEECandidateCellInset\relax}{%
    \centering\NPEECandidateLabelFace #2\strut}}
\newcommand{\NPEEEnableCandidateInfo}{\NPEECandidateInfotrue}
\newcommand{\NPEEDisableCandidateInfo}{\NPEECandidateInfofalse}
\newcommand{\NPEEEnableCandidateNotices}{\NPEECandidateNoticestrue}
\newcommand{\NPEEDisableCandidateNotices}{\NPEECandidateNoticesfalse}
\newcommand{\NPEEEnablePaperOpening}{\NPEEPaperOpeningtrue}
\newcommand{\NPEEDisablePaperOpening}{\NPEEPaperOpeningfalse}
\newcommand{\NPEESetCandidateInfoLayout}[2]{%
  \setlength{\NPEECandidateLabelWidth}{#1}%
  \setlength{\NPEECandidateRowHeight}{#2}%
  \setlength{\NPEECandidateNumberRowHeight}{#2}%
  \setlength{\NPEECandidateNameRowHeight}{#2}}
\NPEEDeclareSetupKeys{
  opening/show/.is if=NPEEPaperOpening,
  paper-opening/show/.is if=NPEEPaperOpening,
  candidate-info/show/.is if=NPEECandidateInfo,
  candidate-notices/show/.is if=NPEECandidateNotices,
  candidate-info/notices-show/.is if=NPEECandidateNotices,
  candidate-info/label-width/.code={%
    \setlength{\NPEECandidateLabelWidth}{#1}},
  candidate-info/row-height/.code={%
    \setlength{\NPEECandidateRowHeight}{#1}%
    \setlength{\NPEECandidateNumberRowHeight}{#1}%
    \setlength{\NPEECandidateNameRowHeight}{#1}},
  candidate-info/number-row-height/.code={%
    \setlength{\NPEECandidateNumberRowHeight}{#1}},
  candidate-info/name-row-height/.code={%
    \setlength{\NPEECandidateNameRowHeight}{#1}},
  candidate-info/cell-inset/.code={%
    \setlength{\NPEECandidateCellInset}{#1}},
  candidate-info/label-font/.code={%
    \renewcommand{\NPEECandidateLabelFace}{#1}}
}

\newcommand{\NPEECandidateNoticeHeading}{考生注意事项}

\newcommand{\NPEECandidateInformationHeading}{（以下信息考生必须认真填写）}

\newcommand{\NPEECandidateNumberLabel}{考生编号}

\newcommand{\NPEECandidateNameLabel}{考生姓名}

% Vertical rhythm around the candidate-information grid.  Projects may
% override this without replacing the page renderer; the default preserves
% the established examination layout.
\newcommand{\NPEECandidateTableTopSkip}{9mm}

\newcommand{\NPEECandidateNotices}{%
  \NPEECandidateNotice{1}{答题前，考生须在试题册指定位置上填写考生编号和考生姓名；在答题卡指定位置上填写报考单位、考生姓名和考生编号，并涂写考生编号信息点。}%
  \NPEECandidateNotice{2}{选择题的答案必须涂写在答题卡相应题号的选项上，非选择题的答案必须书写在答题卡指定位置的边框区域内。超出答题区域书写的答案无效；在草稿纸、试题册上答题无效。}%
  \NPEECandidateNotice{3}{填（书）写部分必须使用黑色字迹签字笔书写，字迹工整、笔迹清楚；涂写部分必须使用 2B 铅笔填涂。}%
  \NPEECandidateNotice{4}{考试结束后，将答题卡和试题册按规定交回。}}

\newcommand{\NPEESetCandidateInfo}[5]{%
  \renewcommand{\NPEECandidateNoticeHeading}{#1}%
  \renewcommand{\NPEECandidateInformationHeading}{#2}%
  \renewcommand{\NPEECandidateNumberLabel}{#3}%
  \renewcommand{\NPEECandidateNameLabel}{#4}%
  \renewcommand{\NPEECandidateNotices}{#5}}

\newcommand{\NPEEFormatPaperHeading}[1]{%
  \ifx\NPEECurrentPaperHeading\@empty
    第#1套%
  \else
    \NPEECurrentPaperHeading%
  \fi}

% Print only the examination subject-code line.  The code is document metadata
% (for example 301/302/303), while the reusable class supplies the neutral
% label and deliberately adds no surrounding punctuation or subject text.
\newcommand{\NPEEFormatSubjectCode}[1]{%
  \edef\NPEETempSubjectCode{#1}%
  \ifx\NPEETempSubjectCode\@empty
  \else
    （科目代码：#1）%
  \fi}

\newcommand{\NPEESetCandidateNotices}[1]{\renewcommand{\NPEECandidateNotices}{#1}}
\newcommand{\NPEECandidateInfoPage}{%
  \ifNPEEAfour
    \setlength{\NPEECandidateLabelWidth}{31.5mm}%
    \setlength{\NPEECandidateRowHeight}{\NPEECandidateAfourRowHeight}%
    \setlength{\NPEECandidateNumberRowHeight}{\NPEECandidateAfourNumberRowHeight}%
    \setlength{\NPEECandidateNameRowHeight}{\NPEECandidateAfourNameRowHeight}%
    \def\NPEECandidateTopSkip{35.5mm}%
    \def\NPEECandidateCodeSkip{7.2mm}%
    \def\NPEECandidateNoticeTitleSkip{16.5mm}%
    \def\NPEECandidateNoticeBeforeSkip{5.8mm}%
    \def\NPEECandidateNoticeAfterSkip{5.8mm}%
    \def\NPEECandidateTableSkip{\NPEECandidateTableTopSkip}%
  \else
    % A landscape spread contains two logical pages.  This left-page-only block
    % needs a denser rhythm than the A4 title page to align with the exam
    % content beginning on the facing page.
    \setlength{\NPEECandidateLabelWidth}{31.5mm}%
    \setlength{\NPEECandidateRowHeight}{8.3mm}%
    \setlength{\NPEECandidateNumberRowHeight}{8.3mm}%
    \setlength{\NPEECandidateNameRowHeight}{8.3mm}%
    \def\NPEECandidateTopSkip{35mm}%
    \def\NPEECandidateCodeSkip{5.8mm}%
    % This value is calibrated for a two-line opening block (paper title plus
    % subject line), which is the stock layout used by the reference exam.
    \def\NPEECandidateNoticeTitleSkip{18.5mm}%
    % On the spread stock the notice paragraph sits close to its heading, while
    % the following parenthetical heading deliberately closes up to the last
    % notice line.  Keep these two pieces of spacing independent: treating
    % them as one shared skip was the source of the visibly low table block.
    \def\NPEECandidateNoticeBeforeSkip{0mm}%
    \def\NPEECandidateNoticeAfterSkip{13mm}%

    \def\NPEECandidateTableSkip{12.5mm}%
  \fi
  % The reference stock leaves a very small optical inset around the grid.
  % Keep the surrounding notice text at the full column width, but reserve
  % 2 mm for the table itself so its outer rules do not visually touch the
  % column edges after device-font rasterisation.
  \setlength{\NPEECandidateDigitWidth}{\dimexpr(\linewidth-\NPEECandidateLabelWidth-2mm-17\arrayrulewidth)/15\relax}%
  \noindent\begin{minipage}[t]{\linewidth}%
  \vspace*{\NPEECandidateTopSkip}%
  \begin{center}
    {\NPEEHeadingFace\fontsize{15pt}{19pt}\selectfont
      \NPEEFormatPaperHeading{\NPEEFormatPaperNumber}\par}
    \ifNPEECandidateInfo
      \vspace{\NPEECandidateCodeSkip}%
      {\NPEEBodyFace\fontsize{10pt}{13.5pt}\selectfont
        \NPEEFormatSubjectCode{\NPEESubjectCode}\par}
    \else\ifNPEECandidateNotices
      \vspace{\NPEECandidateCodeSkip}%
      {\NPEEBodyFace\fontsize{10pt}{13.5pt}\selectfont
        \NPEEFormatSubjectCode{\NPEESubjectCode}\par}
    \fi\fi
    \ifNPEECandidateNotices
      \vspace{\NPEECandidateNoticeTitleSkip}%
      % The reference paper uses a Song-style Chinese face for this heading,
      % rather than the heavier sans/Hei heading face used by section titles.
      % Keep the existing size and placement, but use the body CJK face with a
      % restrained bold weight so the notice reads like a printed examination
      % form instead of a display heading.
      {\NPEEBodyFace\bfseries\fontsize{15pt}{18.5pt}\selectfont
        \NPEECandidateNoticeHeading\par}
    \fi
  \end{center}
  \ifNPEECandidateNotices
    \vspace{\NPEECandidateNoticeBeforeSkip}%
    {\NPEEBodyFace\fontsize{10.5pt}{14.2pt}\selectfont
      \NPEECandidateNotices}
    \vspace{\NPEECandidateNoticeAfterSkip}%
  \fi
  \ifNPEECandidateInfo
    \begin{center}
      {\NPEEBodyFace\fontsize{11pt}{14.5pt}\selectfont \NPEECandidateInformationHeading\par}
      \vspace{\NPEECandidateTableSkip}%
      \renewcommand{\arraystretch}{1}%
      \setlength{\arrayrulewidth}{.35pt}%
      \setlength{\tabcolsep}{0pt}%
      \hspace*{1mm}%
      \begin{tabular}{|>{\centering\arraybackslash}m{\NPEECandidateLabelWidth}|*{15}{>{\centering\arraybackslash}m{\NPEECandidateDigitWidth}|}}
        \hline
        \NPEECandidateCellWithHeight{\NPEECandidateNumberRowHeight}{\NPEECandidateNumberLabel} & & & & & & & & & & & & & & & \\
        \hline
        \NPEECandidateCellWithHeight{\NPEECandidateNameRowHeight}{\NPEECandidateNameLabel} & \multicolumn{15}{c|}{} \\
        \hline
      \end{tabular}\par
    \end{center}%
  \fi
  \end{minipage}}

\newcommand{\NPEERenderCandidateOpening}{%
  \def\NPEECandidateOpeningBreakAction{}%
  \ifNPEEPaperOpening
    \ifNPEEOpeningPage
      \NPEECandidateInfoPage
      \def\NPEECandidateOpeningBreakAction{\NPEEExamColumnBreak}%
    \else
      % Keep the paper identity visible without manufacturing an empty first
      % page when both optional examination-information blocks are hidden.
      \par\addvspace{2mm}\noindent
      \begin{center}
        {\NPEEHeadingFace\fontsize{15pt}{19pt}\selectfont
          \NPEEFormatPaperHeading{\NPEEFormatPaperNumber}\par}
      \end{center}
      \vspace{1mm}\noindent
    \fi
  \fi
  \NPEECandidateOpeningBreakAction}
\AddToHook{npee-exam/paper/opening}{\NPEERenderCandidateOpening}




% -----------------------------------------------------------------------------
% Feature section: paper flow and sections
% -----------------------------------------------------------------------------

\newcommand{\NPEEExamSectionHeading}{}
\newcommand{\NPEEResolveExamSectionHeading}[1]{%
  \def\NPEEExamSectionHeading{}%
  \def\NPEETempSectionTitle{#1}%
  \ifnum\pdfstrcmp{\NPEETempSectionTitle}{\NPEEChoiceSectionTitle}=0
    \def\NPEEExamSectionHeading{\NPEEChoiceSectionInstruction}%
  \else\ifnum\pdfstrcmp{\NPEETempSectionTitle}{\NPEEFillSectionTitle}=0
    \def\NPEEExamSectionHeading{\NPEEFillSectionInstruction}%
  \else\ifnum\pdfstrcmp{\NPEETempSectionTitle}{\NPEESolutionSectionTitle}=0
    \def\NPEEExamSectionHeading{\NPEESolutionSectionInstruction}%
  \fi\fi\fi}
\newcommand{\NPEEExamFirstSection}{%
  \NPEEResolveExamSectionHeading{\NPEEChoiceSectionTitle}%
  \NPEEExamBeginColumns
  \def\NPEEFirstSectionBreakAction{\par\vspace*{0pt}}%
  \ifnum\value{npeeexamsection}=0
    % Keep the default action selected above.
  \else
    \def\NPEEFirstSectionBreakAction{\par\NPEEExamColumnBreak}%
  \fi
  \NPEEFirstSectionBreakAction
  \refstepcounter{npeeexamsection}%
  \par\addvspace{\NPEESectionBeforeSkip}%
  \noindent{\NPEEHeadingFace\fontsize{\NPEESectionTitleSize}{\NPEESectionTitleLineHeight}\selectfont%
    \NPEEFormatSectionNumber\NPEESectionNumberSeparator
    \NPEEChoiceSectionTitle\NPEESectionTitleSeparator
    \NPEEExamSectionHeading\NPEESectionTerminalPunctuation\par}
  % The reference first column keeps the first question close to the
  % instruction block; later section transitions retain the normal rhythm.
  \ifnum\value{npeeexamsection}=1\relax
    \vspace{-1.5mm}%
  \else
    \vspace{.5mm}%
  \fi}

\newcommand{\NPEEChoiceSectionTitle}{选择题}

\newcommand{\NPEEFillSectionTitle}{填空题}

\newcommand{\NPEESolutionSectionTitle}{解答题}

\newcommand{\NPEEResetSolutionSectionIfNeeded}[1]{%
  \def\NPEETempSectionTitle{#1}%
  \ifnum\pdfstrcmp{\NPEETempSectionTitle}{\NPEESolutionSectionTitle}=0
    \NPEEResetSolutionFlow
  \fi}

\newcommand{\NPEEChoiceSectionInstruction}{1～10小题，每小题5分，共50分。下列每题给出的四个选项中，只有一个选项是最符合题目要求的}

\newcommand{\NPEEFillSectionInstruction}{11～16小题，每小题5分，共30分}

\newcommand{\NPEESolutionSectionInstruction}{17～22小题，共70分。解答应写出文字说明、证明过程或演算步骤}

\newcommand{\NPEESetSectionTitles}[3]{%
  \renewcommand{\NPEEChoiceSectionTitle}{#1}%
  \renewcommand{\NPEEFillSectionTitle}{#2}%
  \renewcommand{\NPEESolutionSectionTitle}{#3}}

\newcommand{\NPEESetSectionInstructions}[3]{%
  \renewcommand{\NPEEChoiceSectionInstruction}{#1}%
  \renewcommand{\NPEEFillSectionInstruction}{#2}%
  \renewcommand{\NPEESolutionSectionInstruction}{#3}}
\newcommand{\NPEEExamRegularSection}[1]{%
  \NPEEResetSolutionSectionIfNeeded{#1}%
  \NPEEResolveExamSectionHeading{#1}%
  \NPEEExamBeginColumns
  % Select the transition before emitting it so a column output routine never
  % runs from inside the section-number conditional.
  \def\NPEERegularSectionBreakAction{\par\vspace*{2.8mm}}%
  \ifnum\value{npeeexamsection}=0
  \else
    \def\NPEERegularSectionBreakAction{\par\NPEEExamColumnBreak}%
  \fi
  \NPEERegularSectionBreakAction
  \refstepcounter{npeeexamsection}%
  \par\addvspace{1.4mm}%
  \noindent{\NPEEHeadingFace\fontsize{\NPEESectionTitleSize}{\NPEESectionTitleLineHeight}\selectfont%
    \NPEEFormatSectionNumber\NPEESectionNumberSeparator
    #1\NPEESectionTitleSeparator\NPEEExamSectionHeading
    \NPEESectionTerminalPunctuation\par}
  \vspace{.5mm}}
\newcommand{\NPEEExamSection}[1]{%
  % A solution section has a stronger contract than an ordinary section.  The
  % dispatch action is resolved first, keeping any page/column transition out
  % of the surrounding \ifnum branch.
  \def\NPEETempSectionTitle{#1}%
  \def\NPEESectionDispatchAction{\NPEEExamRegularSection{#1}}%
  \ifnum\pdfstrcmp{\NPEETempSectionTitle}{\NPEESolutionSectionTitle}=0
    \def\NPEESectionDispatchAction{\NPEEExamSolutionContinue}%
  \fi
  \NPEESectionDispatchAction}
\newcommand{\NPEEExamRegularSectionContinue}[1]{%
  \NPEEResolveExamSectionHeading{#1}%
  \NPEEExamBeginColumns
  \refstepcounter{npeeexamsection}%
  \par\addvspace{\dimexpr\NPEESectionBeforeSkip+0.8mm\relax}%
  \noindent{\NPEEHeadingFace\fontsize{\NPEESectionTitleSize}{\NPEESectionTitleLineHeight}\selectfont%
    \NPEEFormatSectionNumber\NPEESectionNumberSeparator
    #1\NPEESectionTitleSeparator\NPEEExamSectionHeading
    \NPEESectionTerminalPunctuation\par}%
  \vspace{.5mm}}
\newcommand{\NPEEExamSectionContinue}[1]{%
  \NPEEResetSolutionSectionIfNeeded{#1}%
  % Resolve the solution/ordinary continuation before executing the selected
  % branch; the solution transition may emit a column penalty.
  \def\NPEESectionContinueAction{\NPEEExamRegularSectionContinue{#1}}%
  \ifnum\pdfstrcmp{#1}{\NPEESolutionSectionTitle}=0
    \def\NPEESectionContinueAction{\NPEEExamSolutionContinue}%
  \fi
  \NPEESectionContinueAction}
\newcommand{\NPEEExamSolutionHeading}{%
  \NPEEResetSolutionFlow
  \refstepcounter{npeeexamsection}%
  \vspace*{3mm}%
  \noindent{\NPEEHeadingFace\fontsize{\NPEESectionTitleSize}{\NPEESectionTitleLineHeight}\selectfont
    \NPEEFormatSectionNumber\NPEESectionNumberSeparator
    \NPEESolutionSectionTitle\NPEESectionTitleSeparator%
    \NPEESolutionSectionInstruction\NPEESectionTerminalPunctuation\par}
  \vspace{.5mm}\ignorespaces}
\newcommand{\NPEEExamSolutionContinue}{%
  \NPEEExamBeginColumns
  % Natural solution structure keeps the solution section in the current flow.
  % Compact spacing always uses this natural-flow contract; other historical
  % structures retain their explicit page/column transitions.
  \def\NPEESolutionTransitionAction{\par}%
  \ifNPEECompact
  \else
    \ifnum\pdfstrcmp{\NPEESolutionStructure}{\NPEESolutionStructureNatural}=0
    \else
      \ifNPEEAfour
        \ifNPEEAnswerLayout
          \def\NPEESolutionTransitionAction{\NPEEAdvanceToAfourSolutionPage}%
        \fi
      \else
        % A3's first response pair occupies the fourth logical page, i.e. the
        % facing column after the three logical objective pages.
        \def\NPEESolutionTransitionAction{\NPEEAdvanceToAthreeSolutionColumn}%
      \fi
    \fi
  \fi
  \NPEESolutionTransitionAction
  % Keep the first structural response pair together when the A4 flow reaches
  % the solution section.  On A4 the pair is allowed to use the remaining
  % portion of page four, so do not reserve a full untouched page here.  The
  % cell heights are adapted immediately after the heading is typeset.
  \def\NPEESolutionReserveAction{}%
  \ifNPEEAnswerLayout
    \ifNPEEAfour
      \ifnum\pdfstrcmp{\NPEESolutionStructure}{\NPEESolutionStructurePairFirst}=0
        % A small guard keeps the heading from becoming the final orphaned
        % line of a nearly full objective page.  The response cells themselves
        % are sized from the actual remaining page height below.
        \def\NPEESolutionReserveAction{\Needspace{4\baselineskip}}%
      \fi
    \fi
  \fi
  \NPEESolutionReserveAction
  \NPEEExamSolutionHeading
  \NPEEAdaptAfourSolutionPairCells}

% A3 spreads number their two columns as consecutive logical pages.  End the
% current spread only when the objective material has not yet reached logical
% page 3, then move to its facing column so the first response pair starts on 4.
\newcommand{\NPEEAdvanceToAthreeSolutionColumn}{%
  \def\NPEEAthreeSolutionAdvanceAction{\NPEEExamColumnBreak}%
  \ifnum\value{npeelogicalpage}<3\relax
    \def\NPEEAthreeSolutionAdvanceAction{%
      \NPEEExamEndColumns\clearpage\NPEEExamBeginColumns\NPEEExamColumnBreak}%
  \fi
  \NPEEAthreeSolutionAdvanceAction}

% Spaced A4 response questions are placed after the objective material has
% reached the fourth physical page.  Compact A4 never calls this helper.
\newcommand{\NPEEAdvanceToAfourSolutionPage}{%
  \def\NPEEAdvanceAction{}%
  \ifNPEEAfour
    \ifnum\value{npeelogicalpage}<4\relax
      \def\NPEEAdvanceAction{\null\clearpage}%
    \fi
  \fi
  \NPEEAdvanceAction
  \def\NPEEAdvanceAction{}%
  \ifNPEEAfour
    \ifnum\value{npeelogicalpage}<4\relax
      \def\NPEEAdvanceAction{\null\clearpage}%
    \fi
  \fi
  \NPEEAdvanceAction
  \def\NPEEAdvanceAction{}%
  \ifNPEEAfour
    \ifnum\value{npeelogicalpage}<4\relax
      \def\NPEEAdvanceAction{\null\clearpage}%
    \fi
  \fi
  \NPEEAdvanceAction}

\newif\ifNPEEFirstSolutionCell
\NPEEFirstSolutionCellfalse
\newcommand{\NPEEResetSolutionFlow}{%
  \setcounter{npeesolutionquestion}{0}%
  \NPEEFirstSolutionCellfalse
  % A previous A4 paper may have adapted its first pair to a partial page.
  % Recompute the stock defaults before the next paper starts so response
  % geometry never leaks across papers in a collection.
  \NPEEUpdateAnswerSlotDimensions}
\AddToHook{npee-exam/paper/start}{\NPEEResetSolutionFlow}
\AddToHook{npee-exam/paper/end}{\NPEEResetSolutionFlow}
\AddToHook{npee-exam/transition}{\NPEEResetSolutionFlow}
\newcommand{\NPEEExamSolutionHere}{%
  % Spaced A4 responses start on a fresh physical page so their first pair of
  % cells stays together.  Compact A4 remains natural-flow even when this
  % compatibility command is present; a spread starts responses in a new column.
  \NPEEExamBeginColumns
  \def\NPEESolutionHereAction{}%
  \ifNPEECompact
  \else
    \ifNPEEAnswerLayout
      \ifNPEEAfour
        \def\NPEESolutionHereAction{\clearpage}%
      \else
        % A spread advances to the facing logical column without discarding it.
        \def\NPEESolutionHereAction{\NPEEExamColumnBreak}%
      \fi
    \fi
  \fi
  \NPEESolutionHereAction
  \NPEEFirstSolutionCelltrue
  \NPEEExamSolutionHeading}

\newenvironment{NPEEExamQuestion}{%
  \par\addvspace{\NPEEQuestionBeforeSkip}%
  \refstepcounter{npeeexamquestion}%
  \begingroup
  \NPEEBodyFace
  % Use the class body setting consistently in questions and answer cells.
  \NPEEApplyBodyStyle
  \clubpenalty=10000\widowpenalty=10000\displaywidowpenalty=10000
  \noindent\hangindent=4.8mm\hangafter=1
  {\NPEEBodyFace\thenpeeexamquestion.}\hspace{.18em}\ignorespaces
}{%
  \par\endgroup
}

% Keep the score label of every solution question identical across papers.
% The label is configurable, while the default remains byte-for-byte
% compatible with the current papers.  The numeric value is also accumulated
% per paper for answer-key and QA tooling.

\newcommand{\NPEEQuestionPointsLabel}[1]{%
  \textup{\NPEEQuestionPointsPrefix#1\NPEEQuestionPointsSuffix}}
\newcommand{\NPEESetQuestionPointsFormat}[2]{%
  \renewcommand{\NPEEQuestionPointsPrefix}{#1}%
  \renewcommand{\NPEEQuestionPointsSuffix}{#2}%
  \renewcommand{\NPEEQuestionPointsLabel}[1]{%
    \textup{\NPEEQuestionPointsPrefix##1\NPEEQuestionPointsSuffix}}}
\newcommand{\NPEEQuestionPointsPrefix}{（本题满分}

\newcommand{\NPEEQuestionPointsSuffix}{分）}
\newcommand{\NPEESetQuestionPointsStyle}[1]{%
  \renewcommand{\NPEEQuestionPointsLabel}[1]{{#1{##1}}}}
\newcommand{\NPEERegisterQuestionPoints}[1]{%
  \addtocounter{npeetotalpoints}{#1}}
\newcommand{\NPEEPrintQuestionPoints}[1]{%
  \NPEEQuestionPointsLabel{#1}\ignorespaces}
\newcommand{\NPEEQuestionPoints}[1]{%
  \NPEERegisterQuestionPoints{#1}%
  \NPEEPrintQuestionPoints{#1}}
\newcommand{\NPEETotalPoints}{\arabic{npeetotalpoints}}




% -----------------------------------------------------------------------------
% Feature section: question widgets
% -----------------------------------------------------------------------------

\RequirePackage{newunicodechar}

\newlength{\NPEEBlankWidth}
\setlength{\NPEEBlankWidth}{17mm}
\newcommand{\NPEESelection}{%
  \ifmmode
    \mathord{\text{\NPEELeftParenthesis\hspace{2.1em}\NPEERightParenthesis}}%
  \else
    \mbox{\NPEELeftParenthesis\hspace{2.1em}\NPEERightParenthesis}%
  \fi}
\newcommand{\NPEEBlank}[1][\NPEEBlankWidth]{%
  \ifmmode
    \mathord{\underline{\hspace{#1}}}%
  \else
    \leavevmode\underline{\hspace{#1}}%
  \fi}
% Tall formulas retain TeX's natural height and baseline.
\newcommand{\NPEEInlineMath}[1]{\ensuremath{#1}}
\newcommand{\NPEEQuestionContinuation}{%
  \par\noindent\hspace*{4.8mm}\ignorespaces}

\newcommand{\NPEEAnswerSpace}[1]{%
  \ifNPEEAnswerLayout
    \par\nobreak\vspace{1.2mm}%
    \ifNPEEInAnswerCell
      \vfill
    \else
      \noindent\rule{0pt}{#1}\par
    \fi
  \fi}
% Response-slot dimensions are implementation details of the selected paper
% stock.  They are deliberately not part of the paper/source API: automatic
% solution questions select a structural slot and the class derives the slot
% size from the active page geometry.
\newlength{\NPEEAnswerHalfHeight}
\newlength{\NPEEAnswerFullHeight}
\newlength{\NPEEAnswerSlotInset}
% Leave a small, symmetric breathing room inside a logical response column.
% The actual slot is derived from the selected paper stock rather than exposed
% as a document setting.  The zero values below are only initialization before
% \textheight is available; every paper lifecycle derives the real slots.
\setlength{\NPEEAnswerSlotInset}{5mm}
\setlength{\NPEEAnswerHalfHeight}{0pt}
\setlength{\NPEEAnswerFullHeight}{0pt}

% The first structural solution group is a pair of equal response cells.  On
% A4 their height is adapted at the solution heading so objective material
% that spills onto page four can share the page with 17--18; on a spread the stock
% height is retained for the logical-column flow.
\newlength{\NPEESolutionPairGap}
\setlength{\NPEESolutionPairGap}{3mm}
\newlength{\NPEESolutionPairHeadingReserve}
\setlength{\NPEESolutionPairHeadingReserve}{15mm}
\newlength{\NPEEAvailableSolutionPairHeight}
\newlength{\NPEESolutionPairGapsHeight}
% Reserve one ordinary baseline for the paragraph/minipage glue that TeX
% adds around a stacked pair.  Without this small safety allowance a pair
% whose arithmetic height exactly equals the remaining page can be moved as
% a whole to the next page by the page builder.
\newlength{\NPEESolutionPairSafety}
\setlength{\NPEESolutionPairSafety}{4mm}

\newcommand{\NPEEUpdateAnswerSlotDimensions}{%
  % The complete response unit must fit within one current logical column.
  % Derive the leading group from its requested structure, including every
  % inter-cell gap, so pair-count is semantic rather than a hidden geometry
  % knob.  The small inset absorbs paragraph/minipage rounding at a column
  % boundary.
  \setlength{\NPEEAnswerFullHeight}{\dimexpr\textheight-\NPEEAnswerSlotInset\relax}%
  \@tempcnta=\NPEESolutionPairCount\relax
  \advance\@tempcnta by -1\relax
  \setlength{\NPEESolutionPairGapsHeight}{\NPEESolutionPairGap}%
  \multiply\NPEESolutionPairGapsHeight by \@tempcnta\relax
  \setlength{\NPEEAnswerHalfHeight}{\dimexpr
    \NPEEAnswerFullHeight-\NPEESolutionPairGapsHeight-
    \NPEESolutionPairHeadingReserve\relax}%
  \divide\NPEEAnswerHalfHeight by \NPEESolutionPairCount\relax}
\AtBeginDocument{\NPEEUpdateAnswerSlotDimensions}

% On A4 answer stock, the objective section may legitimately continue onto
% page four.  The first two solution questions must still begin there, so
% their response cells are derived from the space that remains after the
% solution heading instead of assuming an untouched page.  This is a
% structural calculation, not a question-level height setting: objective
% questions keep their natural flow and 17--18 share whatever usable area is
% left on the fourth page.
\newcommand{\NPEEAdaptAfourSolutionPairCells}{%
  \ifNPEEAnswerLayout
    \ifNPEEAfour
      \ifnum\pdfstrcmp{\NPEESolutionStructure}{\NPEESolutionStructurePairFirst}=0
        \@tempcnta=\NPEESolutionPairCount\relax
        \advance\@tempcnta by -1\relax
        \setlength{\NPEESolutionPairGapsHeight}{\NPEESolutionPairGap}%
        \multiply\NPEESolutionPairGapsHeight by \@tempcnta\relax
        \setlength{\NPEEAvailableSolutionPairHeight}{\dimexpr
          \pagegoal-\pagetotal-\NPEESolutionPairGapsHeight-
          \NPEEAnswerSlotInset-\NPEESolutionPairSafety\relax}%
        \ifdim\NPEEAvailableSolutionPairHeight>0pt\relax
          \setlength{\NPEEAnswerHalfHeight}{\NPEEAvailableSolutionPairHeight}%
          \divide\NPEEAnswerHalfHeight by \NPEESolutionPairCount\relax
        \fi
      \fi
    \fi
  \fi}

% Solution pagination is a structural policy.  Source papers describe only
% the question and its score; the class decides how response cells are
% grouped for the selected stock.  ``pair-first'' is the ordinary Chinese
% examination rhythm: the first two solution questions share an A4 page and
% every later question starts on a fresh page.  ``natural'' retains the
% legacy flowing behaviour, while ``full-page'' gives every solution question
% its own full response page.
\newcommand{\NPEESolutionStructure}{pair-first}
\newcommand{\NPEESolutionPairCount}{2}
\newcommand{\NPEESolutionStructurePairFirst}{pair-first}
\newcommand{\NPEESolutionStructureNatural}{natural}
\newcommand{\NPEESolutionStructureFullPage}{full-page}
\newcommand{\NPEESetSolutionStructure}[1]{%
  \edef\NPEETempSolutionStructure{#1}%
  \ifnum\pdfstrcmp{\NPEETempSolutionStructure}{\NPEESolutionStructurePairFirst}=0
    \renewcommand{\NPEESolutionStructure}{pair-first}%
  \else\ifnum\pdfstrcmp{\NPEETempSolutionStructure}{\NPEESolutionStructureNatural}=0
    \renewcommand{\NPEESolutionStructure}{natural}%
  \else\ifnum\pdfstrcmp{\NPEETempSolutionStructure}{\NPEESolutionStructureFullPage}=0
    \renewcommand{\NPEESolutionStructure}{full-page}%
  \else
    \NPEEWarningNoLine{npee-math-exam}{Unknown solution structure `#1'; using pair-first}%
    \renewcommand{\NPEESolutionStructure}{pair-first}%
  \fi\fi\fi}
\newcommand{\NPEESetSolutionPairCount}[1]{%
  \@tempcnta=#1\relax
  \ifnum\@tempcnta<1
    \NPEEWarningNoLine{npee-math-exam}{Solution pair-count must be positive; using 2}%
    \renewcommand{\NPEESolutionPairCount}{2}%
  \else
    \ifnum\@tempcnta>8\relax
      \NPEEWarningNoLine{npee-math-exam}{Solution pair-count must not exceed 8; using 8}%
      \renewcommand{\NPEESolutionPairCount}{8}%
    \else
      \edef\NPEESolutionPairCount{\number\@tempcnta}%
    \fi
  \fi
  \NPEEUpdateAnswerSlotDimensions}
\NPEEDeclareSetupKeys{
  solution/structure/.code={\NPEESetSolutionStructure{#1}},
  solution/layout/.code={\NPEESetSolutionStructure{#1}},
  solution/pair-count/.code={\NPEESetSolutionPairCount{#1}}
}

\newif\ifNPEESolutionCellActive
\newif\ifNPEESolutionHalfCell
\newif\ifNPEELegacySolutionHeightWarningIssued
\NPEESolutionCellActivefalse
\NPEESolutionHalfCellfalse
\NPEELegacySolutionHeightWarningIssuedfalse
\newcommand{\NPEEWarnLegacySolutionHeight}{%
  \ifNPEELegacySolutionHeightWarningIssued\else
    \NPEEWarningNoLine{npee-math-exam}{Explicit solution heights are deprecated; configure solution structure instead}%
    \global\NPEELegacySolutionHeightWarningIssuedtrue
  \fi}
% Resolve one response slot in small helpers.  Each helper closes all of its
% conditionals before returning: a fixed cell can make `multicols*' enter its
% output routine as soon as it is boxed, and that routine must not inherit a
% still-open selector branch.
\newcommand{\NPEEPrepareAfourSolutionCell}{%
  \ifnum\pdfstrcmp{\NPEESolutionStructure}{\NPEESolutionStructurePairFirst}=0
    \NPEESolutionCellActivetrue
    \ifnum\value{npeesolutionquestion}>\NPEESolutionPairCount\relax
      \def\NPEEAutomaticSolutionPageAction{\clearpage}%
    \else
      \NPEESolutionHalfCelltrue
    \fi
  \fi
  \ifnum\pdfstrcmp{\NPEESolutionStructure}{\NPEESolutionStructureFullPage}=0
    \NPEESolutionCellActivetrue
    \NPEEFirstSolutionCellfalse
    \ifnum\value{npeesolutionquestion}>1\relax
      \def\NPEEAutomaticSolutionPageAction{\clearpage}%
    \fi
  \fi}
\newcommand{\NPEEPrepareSpreadSolutionCell}{%
  % The opening group is stacked in one logical column.  Later questions own
  % one complete column and naturally advance into the facing column.
  \ifnum\pdfstrcmp{\NPEESolutionStructure}{\NPEESolutionStructurePairFirst}=0
    \NPEESolutionCellActivetrue
    \ifnum\value{npeesolutionquestion}>\NPEESolutionPairCount\relax
    \else
      \NPEESolutionHalfCelltrue
    \fi
  \fi}
\newcommand{\NPEEPrepareAutomaticSolutionCell}{%
  \stepcounter{npeesolutionquestion}%
  % Automatic layout is structural.  A natural flow receives no response slot.
  \def\NPEESolutionAnswerHeight{0pt}%
  \def\NPEEAutomaticSolutionPageAction{}%
  \NPEESolutionCellActivefalse
  \NPEESolutionHalfCellfalse
  \ifNPEEAnswerLayout
    \ifNPEEAfour
      \NPEEPrepareAfourSolutionCell
    \else
      \NPEEPrepareSpreadSolutionCell
    \fi
  \fi
  % The only page action is emitted after every selector has closed.
  \NPEEAutomaticSolutionPageAction}
\newif\ifNPEEAnswerBreakPending
\NPEEAnswerBreakPendingfalse
\AddToHook{npee-exam/paper/start}{\global\NPEEAnswerBreakPendingfalse}
\AddToHook{npee-exam/paper/end}{\global\NPEEAnswerBreakPendingfalse}
\AddToHook{npee-exam/transition}{\global\NPEEAnswerBreakPendingfalse}
\newcommand{\NPEEConsumeAnswerBreak}{%
  \def\NPEEPendingColumnAction{}%
  \ifNPEEAnswerBreakPending
    \global\NPEEAnswerBreakPendingfalse
    \def\NPEEPendingColumnAction{\NPEEExamColumnBreak}%
  \fi
  % Execute the break after the conditional has closed.  A multicols output
  % routine cannot safely be entered while a source-level \if is open.
  \NPEEPendingColumnAction}
\newcommand{\NPEEQueueAutomaticSolutionBreak}{%
  % ``pair-first'' is deliberately a structural policy: after its first
  % stacked pair, complete response cells advance through the landscape spread by
  % their natural minipage geometry.  Do not queue a second forced break here.
  % An eager columnbreak after every cell skips the facing column and turns a
  % two-column spread into one response page per question.
  %
  % Keep the pending transition only for the legacy full-page policy.  Resolve
  % the state to a plain action first, so a later multicols output routine is
  % never entered while this selector still has an open conditional.
  \def\NPEEAutomaticBreakAction{}%
  \ifNPEEAnswerLayout
    \ifNPEEAfour
    \else
      \ifnum\pdfstrcmp{\NPEESolutionStructure}{\NPEESolutionStructureFullPage}=0
        \def\NPEEAutomaticBreakAction{\global\NPEEAnswerBreakPendingtrue}%
      \fi
    \fi
  \fi
  \NPEEAutomaticBreakAction}
\newenvironment{NPEEAnswerColumn}{%
  \def\NPEEAnswerColumnStartAction{\par\vspace{0pt}}%
  \ifNPEEAfour
  \else
    % A column is a flow boundary, not a boxed answer group.  Keeping an
    % outer minipage here makes the complete 17--18 pair unbreakable in a spread;
    % when the heading consumes the remaining height TeX moves both answers
    % to the next physical sheet.  Let the inner answer cells participate in
    % multicols column breaking instead.
    \def\NPEEAnswerColumnStartAction{\NPEEConsumeAnswerBreak\par\vspace{0pt}}%
  \fi
  \NPEEAnswerColumnStartAction
}{%
  \par}
\newcommand{\NPEEConsumeFirstSolutionCellFlag}{%
  % Decide this state transition before a response minipage is opened.  The
  % A spread multicols output routine may run while a minipage is being started;
  % keeping a raw \if token adjacent to that boundary causes TeX to report an
  % incomplete conditional even though the visual output happens to succeed.
  \def\NPEEFirstSolutionCellAction{}%
  \ifNPEEFirstSolutionCell
    \def\NPEEFirstSolutionCellAction{\global\NPEEFirstSolutionCellfalse}%
  \fi
  \NPEEFirstSolutionCellAction}
\newenvironment{NPEEAnswerCell}{%
  % A first half-height response cell sits directly under the section
  % heading, so no later full-height cell should retain the heading reserve.
  \NPEEConsumeFirstSolutionCellFlag
  \begin{minipage}[t][\NPEEAnswerHalfHeight][t]{\linewidth}%
  \vspace{0pt}%
  \NPEEInAnswerCelltrue
}{%
  \NPEEInAnswerCellfalse
  \end{minipage}}
\newcommand{\NPEEAnswerCellGap}{%
  \par\vspace{\NPEESolutionPairGap}%
}
\newlength{\NPEESolutionHeadingReserve}
% The first full-height response box shares a logical page with the response
% section heading.  Reserve that vertical rhythm in the cell itself instead
% of pushing an otherwise valid first question to the following column.
\setlength{\NPEESolutionHeadingReserve}{35mm}
\newcommand{\NPEEResolveFullAnswerCellHeight}{%
  \def\NPEEAutomaticFullCellHeight{\NPEEAnswerFullHeight}%
  \def\NPEEAutomaticFullCellStateAction{}%
  \ifNPEEFirstSolutionCell
    \def\NPEEAutomaticFullCellHeight{\dimexpr\NPEEAnswerFullHeight-\NPEESolutionHeadingReserve\relax}%
    \def\NPEEAutomaticFullCellStateAction{\global\NPEEFirstSolutionCellfalse}%
  \fi
  \NPEEAutomaticFullCellStateAction}
\newenvironment{NPEEAnswerFullCell}{%
  \NPEEResolveFullAnswerCellHeight
  \begin{minipage}[t][\NPEEAutomaticFullCellHeight][t]{\linewidth}%
  \vspace{0pt}%
  \NPEEInAnswerCelltrue
}{%
  \NPEEInAnswerCellfalse
  \end{minipage}}
% Automatic solution questions use direct minipage actions rather than
% nesting a second LaTeX environment inside ExamSolutionQuestion.  The
% latter is fragile in multicols*: the environment's bookkeeping group can
% be closed by an output routine before the outer question finishes.
\newcommand{\NPEEStartAnswerHalfCell}{%
  \NPEEConsumeFirstSolutionCellFlag
  \begin{minipage}[t][\NPEEAnswerHalfHeight][t]{\linewidth}%
  \vspace{0pt}%
  \NPEEInAnswerCelltrue}
\newcommand{\NPEEStartAnswerFullCell}{%
  % Resolve state before opening a minipage: in a spread this can immediately enter
  % the multicols output routine.
  \NPEEResolveFullAnswerCellHeight
  \begin{minipage}[t][\NPEEAutomaticFullCellHeight][t]{\linewidth}%
  \vspace{0pt}%
  \NPEEInAnswerCelltrue}
\newcommand{\NPEEFinishAnswerCell}{%
  \NPEEInAnswerCellfalse
  \end{minipage}}
\newcommand{\NPEEAnswerSpreadBreak}{%
  % Kept for source compatibility.  In a spread defer the break until the next
  % answer column starts.  A direct \columnbreak at the end of a multicols*
  % body can move the preceding, otherwise fitting answer cells to a fresh
  % physical sheet; a pending break preserves both the intended transition
  % and harmless trailing calls.
  \def\NPEEAnswerSpreadBreakAction{}%
  \ifNPEEAfour
    \def\NPEEAnswerSpreadBreakAction{\clearpage}%
  \else
    % Keep conditionals out of skipped macro bodies: TeX counts raw
    % \iftrue tokens while scanning an inactive branch.
    \def\NPEEAnswerSpreadBreakAction{\NPEEAnswerBreakPendingtrue}%
  \fi
  \NPEEAnswerSpreadBreakAction
  \ignorespaces}
\newcommand{\NPEEAnswerColumnBreak}{%
  % In A4 each answer column is a full physical page.  In a spread the same
  % command advances to the next logical column of the spread.
  \def\NPEEAnswerColumnBreakAction{\clearpage}%
  \ifNPEEAfour
  \else
    \global\NPEEAnswerBreakPendingfalse
    \ifNPEEExamColumnsOpen
      \def\NPEEAnswerColumnBreakAction{\NPEESafeColumnBreak}%
    \fi
  \fi
  \NPEEAnswerColumnBreakAction\ignorespaces}

% --------------------------------------------------------------------------
% Standalone answer-key flow
% --------------------------------------------------------------------------
% Student papers use adaptive A4 half cells and fixed-height spread half cells.
% Answer keys should not inherit either student writing-space policy: this
% flow starts a separate, naturally breaking answer section that can be
% appended to a book or compiled from a wrapper document.

\newlength{\NPEEChoiceIndent}
\setlength{\NPEEChoiceIndent}{5mm}
\NPEEDeclareSetupKeys{
  choices/indent/.code={\setlength{\NPEEChoiceIndent}{#1}},
  blank/width/.code={\setlength{\NPEEBlankWidth}{#1}}
}
\newcommand{\NPEEChoiceText}[2]{\raggedright\textup{#1.}\enspace #2\par}
\newsavebox{\NPEEChoiceMeasureBox}
\newlength{\NPEEChoiceWidest}
\newcommand{\NPEEMeasureChoice}[1]{%
  \sbox{\NPEEChoiceMeasureBox}{\strut #1}%
  \ifdim\wd\NPEEChoiceMeasureBox>\NPEEChoiceWidest
    \setlength{\NPEEChoiceWidest}{\wd\NPEEChoiceMeasureBox}%
  \fi}
\newcommand{\NPEEMeasureChoices}[4]{%
  \setlength{\NPEEChoiceWidest}{0pt}%
  \NPEEMeasureChoice{\textup{A.}\enspace #1}\NPEEMeasureChoice{\textup{B.}\enspace #2}%
  \NPEEMeasureChoice{\textup{C.}\enspace #3}\NPEEMeasureChoice{\textup{D.}\enspace #4}}
\newcommand{\NPEEChoicesOneLine}[4]{%
  \par\vspace{\NPEEChoiceBeforeSkip}\noindent\hspace*{\NPEEChoiceIndent}%
  \begin{minipage}[t]{\dimexpr\linewidth-\NPEEChoiceIndent\relax}\noindent
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{A}{#1}\end{minipage}\hfill
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{B}{#2}\end{minipage}\hfill
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{C}{#3}\end{minipage}\hfill
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{D}{#4}\end{minipage}%
  \end{minipage}\par}
\newcommand{\NPEEChoicesTwoByTwo}[4]{%
  \par\vspace{\NPEEChoiceBeforeSkip}\noindent\hspace*{\NPEEChoiceIndent}%
  \begin{minipage}[t]{\dimexpr\linewidth-\NPEEChoiceIndent\relax}\noindent
    \begin{minipage}[t]{.475\linewidth}\NPEEChoiceText{A}{#1}\end{minipage}\hfill
    \begin{minipage}[t]{.475\linewidth}\NPEEChoiceText{B}{#2}\end{minipage}\par\vspace{\NPEEChoiceBeforeSkip}\noindent
    \begin{minipage}[t]{.475\linewidth}\NPEEChoiceText{C}{#3}\end{minipage}\hfill
    \begin{minipage}[t]{.475\linewidth}\NPEEChoiceText{D}{#4}\end{minipage}%
  \end{minipage}\par}
\newcommand{\NPEEChoicesOnePerLine}[4]{%
  \par\vspace{.5mm}\begingroup
  \leftskip=\NPEEChoiceIndent
  \setcounter{npeechoice}{0}%
  \def\NPEEChoiceItem##1{\refstepcounter{npeechoice}\par\noindent
    \hangindent=5.5mm\hangafter=1\textup{\Alph{npeechoice}.}\enspace ##1}%
  \NPEEChoiceItem{#1}\NPEEChoiceItem{#2}\NPEEChoiceItem{#3}\NPEEChoiceItem{#4}%
  \par\endgroup}
\newcommand{\NPEEChoices}[4]{%
  \NPEEMeasureChoices{#1}{#2}{#3}{#4}%
  % Keep normal body size; long alternatives move to two rows rather than
  % being squeezed into four narrow cells.
  \ifdim\NPEEChoiceWidest<.34\linewidth
    \NPEEChoicesTwoByTwo{#1}{#2}{#3}{#4}%
  \else
    \NPEEChoicesOnePerLine{#1}{#2}{#3}{#4}%
  \fi}
\newcommand{\NPEEGraphicChoices}[4]{%
  \par\vspace{\NPEEChoiceBeforeSkip}\noindent\hspace*{\NPEEChoiceIndent}%
  \begin{minipage}[t]{\dimexpr\linewidth-\NPEEChoiceIndent\relax}\noindent
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{A}{\NPEEChoiceGraphic{#1}}\end{minipage}\hfill
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{B}{\NPEEChoiceGraphic{#2}}\end{minipage}\hfill
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{C}{\NPEEChoiceGraphic{#3}}\end{minipage}\hfill
    \begin{minipage}[t]{.235\linewidth}\NPEEChoiceText{D}{\NPEEChoiceGraphic{#4}}\end{minipage}%
  \end{minipage}\par}

\newcommand{\NPEEResetSubparts}{\setcounter{npeesubpart}{0}}
\newcommand{\NPEESubpart}[1]{%
  \par\addvspace{\NPEESubpartBeforeSkip}\noindent
  \refstepcounter{npeesubpart}\label{npee.subpart.#1}%
  \expandafter\xdef\csname NPEESubpartGlyph@#1\endcsname{(\arabic{npeesubpart})}%
  \hangindent=5.8mm\hangafter=1
  \textup{(\arabic{npeesubpart})}\enspace\ignorespaces}
\newcommand{\NPEESubpartRef}[1]{%
  \hyperref[npee.subpart.#1]{\csname NPEESubpartGlyph@#1\endcsname}}
\newcommand{\NPEEResetCircledItems}{\setcounter{npeecircleditem}{0}}
\newcommand{\NPEECircledDigitFallback}[1]{%
  \tikz[baseline=-.58ex]{%
    \node[draw,circle,inner sep=0pt,outer sep=0pt,
      minimum size=1.18em,line width=.25pt,
      font=\NPEEBodyFace\fontsize{9.2pt}{9.2pt}\selectfont] {#1};}}
\newcommand{\NPEECircledGlyph}[2]{%
  \begingroup
    \NPEECircledFace\fontsize{10.5pt}{10.5pt}\selectfont
    \iffontchar\font"#1
      \char"#1
    \else
      \NPEECircledDigitFallback{#2}%
    \fi
  \endgroup}
\newcommand{\NPEECircledDigitText}[1]{%
  % Prefer the selected CJK font's professionally designed circled glyph.
  % Fall back to a thin, baseline-aligned outline only when the glyph is absent.
  \ifcase#1\relax
  \or\NPEECircledGlyph{2460}{1}%
  \or\NPEECircledGlyph{2461}{2}%
  \or\NPEECircledGlyph{2462}{3}%
  \or\NPEECircledGlyph{2463}{4}%
  \or\NPEECircledGlyph{2464}{5}%
  \or\NPEECircledGlyph{2465}{6}%
  \or\NPEECircledGlyph{2466}{7}%
  \or\NPEECircledGlyph{2467}{8}%
  \or\NPEECircledGlyph{2468}{9}%
  \or\NPEECircledGlyph{2469}{10}%
  \else#1\fi}
\newcommand{\NPEECircledDigit}[1]{%
  \ifmmode
    \mathord{\text{\NPEECircledDigitText{#1}}}%
  \else
    \NPEECircledDigitText{#1}%
  \fi}
% Accept raw circled digits from copied source material, but normalize them
% to the same renderer used by \NPEECircledDigit.
\newunicodechar{①}{\NPEECircledDigit{1}}
\newunicodechar{②}{\NPEECircledDigit{2}}
\newunicodechar{③}{\NPEECircledDigit{3}}
\newunicodechar{④}{\NPEECircledDigit{4}}
\newunicodechar{⑤}{\NPEECircledDigit{5}}
\newunicodechar{⑥}{\NPEECircledDigit{6}}
\newunicodechar{⑦}{\NPEECircledDigit{7}}
\newunicodechar{⑧}{\NPEECircledDigit{8}}
\newunicodechar{⑨}{\NPEECircledDigit{9}}
\newunicodechar{⑩}{\NPEECircledDigit{10}}
\newcommand{\NPEECircledItem}[1]{%
  \refstepcounter{npeecircleditem}%
  \label{npee.circled.#1}%
  \expandafter\xdef\csname NPEECircledGlyph@#1\endcsname{%
    \noexpand\NPEECircledDigit{\arabic{npeecircleditem}}}%
  \NPEECircledDigit{\arabic{npeecircleditem}}\kern.35em}
\newcommand{\NPEECircledItemRef}[1]{%
  \ifcsname NPEECircledGlyph@#1\endcsname
    \hyperref[npee.circled.#1]{\csname NPEECircledGlyph@#1\endcsname}%
  \else
    \NPEEWarning{npee-math-exam}{Unknown circled-item key `#1'}#1%
  \fi}
\newcommand{\NPEECircledStatement}[1]{%
  \refstepcounter{npeecircleditem}%
  \NPEEStatement{\arabic{npeecircleditem}}{#1}}
\newcommand{\NPEEStatementBeforeSkip}{.45mm}
\newcommand{\NPEEStatementLabelGap}{.45em}
\newcommand{\NPEEStatementMarker}[1]{%
  \par\addvspace{\NPEEStatementBeforeSkip}\noindent
  \hangindent=6.2mm\hangafter=1
  \NPEECircledDigit{#1}\hspace{\NPEEStatementLabelGap}\ignorespaces}
\newcommand{\NPEEStatement}[2]{%
  \NPEEStatementMarker{#1}#2\par}
\newcommand{\NPEEStatements}[4]{%
  \NPEEStatement{1}{#1}%
  \NPEEStatement{2}{#2}%
  \NPEEStatement{3}{#3}%
  \NPEEStatement{4}{#4}}
\newcommand{\NPEENaturalNumbers}{\mathbb{N}}




% -----------------------------------------------------------------------------
% Feature section: answer visibility and versions
% -----------------------------------------------------------------------------

% Lightweight answer visibility is useful to question packages that do not
% need the full answer-key document flow.

\NPEEDeclareSetupKeys{
  answers/show/.is if=NPEEAnswerMode
}

\newcommand{\NPEEEnableAnswers}{\NPEEAnswerModetrue}
\newcommand{\NPEEDisableAnswers}{\NPEEAnswerModefalse}
\newcommand{\NPEEIfAnswersTF}[2]{\ifNPEEAnswerMode #1\else #2\fi}
\newcommand{\NPEEAnswerLabel}{参考答案：}
\newcommand{\NPEESetAnswerLabel}[1]{\renewcommand{\NPEEAnswerLabel}{#1}}
\newcommand{\NPEEAnswer}[1]{%
  \ifNPEEAnswerMode
    \par\addvspace{1.2mm}\noindent
    {\NPEEHeadingFace\bfseries\NPEEAnswerLabel}\,#1\par
  \fi}

\newcommand{\ExamSetMode}[1]{%
  \NPEENormalizeValue{#1}%
  \edef\NPEETempMode{\NPEENormalizedValue}%
  \def\NPEEStudentMode{student}%
  \def\NPEETeacherMode{teacher}%
  \def\NPEEKeyMode{key}%
  \def\NPEEAnswerKeyMode{answer-key}%
  \ifx\NPEETempMode\NPEEStudentMode
    \renewcommand{\ExamMode}{student}%
    \NPEEDisableAnswers
  \else\ifx\NPEETempMode\NPEETeacherMode
    \renewcommand{\ExamMode}{teacher}%
    \NPEEEnableAnswers
  \else\ifx\NPEETempMode\NPEEKeyMode
    \renewcommand{\ExamMode}{key}%
    \NPEEEnableAnswers
  \else\ifx\NPEETempMode\NPEEAnswerKeyMode
    \renewcommand{\ExamMode}{answer-key}%
    \NPEEEnableAnswers
  \else
    \NPEEWarning{npee-math-exam}{Unknown mode `#1'; using student mode}%
    \renewcommand{\ExamMode}{student}%
    \NPEEDisableAnswers
  \fi\fi\fi\fi}
\newcommand{\ExamMode}{student}
\newcommand{\ExamSetVersion}[1]{%
  \NPEENormalizeValue{#1}%
  \edef\ExamVersion{\NPEENormalizedValue}}
\newcommand{\ExamVersion}{A}
\newcommand{\ExamVariant}[3]{%
  \ifnum\pdfstrcmp{#1}{\ExamVersion}=0 #2\else #3\fi}




% -----------------------------------------------------------------------------
% Feature section: answer-key document flow
% -----------------------------------------------------------------------------

\RequirePackage{xparse}
\RequirePackage{needspace}

\newif\ifNPEEAnswerKeyActive
\NPEEAnswerKeyActivefalse
% Keep the nested solution state explicit.  Answer-key end hooks may be called
% by wrappers even when no solution block has started, so this flag must exist
% independently of the active answer-key flag.
\newif\ifNPEEAnswerKeySolutionActive
\NPEEAnswerKeySolutionActivefalse
% Track nested solution wrappers so a compatibility end command can close the
% outer block without producing an undefined-control-sequence error.
\newcount\NPEEAnswerKeySolutionNesting
\NPEEAnswerKeySolutionNesting=0
\newif\ifNPEEAnswerKeyPreviousAnswerMode
\NPEEAnswerKeyPreviousAnswerModefalse

\newcommand{\NPEEAnswerKeyNumberWidth}{11mm}
\newcommand{\NPEEAnswerKeyPointsWidth}{16mm}
\newcommand{\NPEEAnswerKeyGap}{.55em}
% A solution block can be opened as an environment by source templates.  The

\newcommand{\NPEEAnswerKeyTitle}{参考答案与解析}

\newcommand{\NPEEAnswerKeyAnswerLabel}{答案}

\newcommand{\NPEEAnswerKeySolutionLabel}{解析}

\newcommand{\NPEEAnswerKeyPointsSuffix}{分}
\newcommand{\NPEESetAnswerKeyTitle}[1]{%
  \renewcommand{\NPEEAnswerKeyTitle}{#1}}
\newcommand{\NPEESetAnswerKeyLabels}[2]{%
  \renewcommand{\NPEEAnswerKeyAnswerLabel}{#1}%
  \renewcommand{\NPEEAnswerKeySolutionLabel}{#2}}
\newcommand{\NPEESetAnswerKeyWidths}[2]{%
  \renewcommand{\NPEEAnswerKeyNumberWidth}{#1}%
  \renewcommand{\NPEEAnswerKeyPointsWidth}{#2}}
\newcommand{\NPEEAnswerKeyRequireActive}{%
  \ifNPEEAnswerKeyActive\else
    \NPEEWarningNoLine{npee-math-exam}{Answer-key content requested before AnswerKeyStart; ignored}%
  \fi}
\NewDocumentCommand{\NPEEAnswerKeyStart}{O{\NPEEAnswerKeyTitle}}{%
  \ifNPEEAnswerKeyActive
    \NPEEWarningNoLine{npee-math-exam}{AnswerKeyStart called while an answer key is already active; ignored}%
  \else
    % Close a student's active paper first.  This preserves its learned page
    % total and makes the answer key a separate bookmarkable flow.
    \ifNPEEExamActive
      \NPEEExamPaperEnd
    \else
      \NPEEExamEndColumns
      \ifnum\value{page}>1\relax\clearpage\fi
      \NPEEDeactivateExamFeatures
    \fi
    \ifNPEEAnswerMode
      \global\NPEEAnswerKeyPreviousAnswerModetrue
    \else
      \global\NPEEAnswerKeyPreviousAnswerModefalse
    \fi
    \global\NPEEAnswerKeyActivetrue
    \NPEEEnableAnswers
    \pagestyle{plain}% answer pages use the ordinary page number
    \NPEEBookmark{#1}{answer-key}%
    \par\addvspace{2mm}\noindent
    \begin{center}
      {\NPEEHeadingFace\bfseries\fontsize{14pt}{18pt}\selectfont #1\par}
    \end{center}
    \vspace{1mm}\nobreak
    \NPEEExamBeginColumns
  \fi}
\newcommand{\NPEEAnswerKeyEnd}{%
  \ifNPEEAnswerKeyActive
    \ifNPEEAnswerKeySolutionActive
      \NPEEWarningNoLine{npee-math-exam}{AnswerKeyEnd closed an unfinished answer-key solution block}%
      \global\NPEEAnswerKeySolutionNesting=0\relax
      \NPEEAnswerKeySolutionEnd
    \fi
    \NPEEExamEndColumns
    \global\NPEEAnswerKeyActivefalse
    \ifNPEEAnswerKeyPreviousAnswerMode
      \NPEEEnableAnswers
    \else
      \NPEEDisableAnswers
    \fi
    \clearpage
    \pagestyle{empty}% keep the book's cover/back matter unnumbered
  \fi}
\newcommand{\NPEEAnswerKeySpreadBreak}{%
  \NPEEAnswerKeyRequireActive
  \ifNPEEAnswerKeyActive
    \NPEEExamEndColumns
    \clearpage
    \NPEEExamBeginColumns
  \fi}
\newcommand{\NPEEAnswerKeySection}[1]{%
  \NPEEAnswerKeyRequireActive
  \ifNPEEAnswerKeyActive
    \NPEEExamBeginColumns
    \par\addvspace{1.4mm}\noindent\nobreak
    {\NPEEHeadingFace\bfseries\fontsize{11.5pt}{15pt}\selectfont #1\par}
    \vspace{.35mm}\nobreak
  \fi}
\newcommand{\NPEEAnswerKeyPointLabel}[1]{%
  \if\relax\detokenize{#1}\relax\else
    \NPEELeftParenthesis#1\NPEEAnswerKeyPointsSuffix\NPEERightParenthesis\fi}
\NewDocumentCommand{\NPEEAnswerKeySolutionStart}{O{}m}{%
  \NPEEAnswerKeyRequireActive
  \ifNPEEAnswerKeyActive
    \ifNPEEAnswerKeySolutionActive
      \global\advance\NPEEAnswerKeySolutionNesting by 1\relax
      \NPEEWarningNoLine{npee-math-exam}{Nested answer-key solution block ignored}%
    \else
      % Keep the numbered heading with the beginning of its explanation.  This
      % matters in a balanced spread multicols flow where only a couple of lines
      % may remain at the bottom of the current column.
      \Needspace{4\baselineskip}%
      \par\addvspace{1.1em}\noindent\nobreak
      \begingroup
        \global\NPEEAnswerKeySolutionActivetrue
        {\NPEEHeadingFace\bfseries
          \makebox[\NPEEAnswerKeyNumberWidth][l]{\textup{#2.}}%
          \makebox[\NPEEAnswerKeyPointsWidth][r]{\NPEEAnswerKeyPointLabel{#1}}\par}
        % `multicols*' balances after the material has been collected, so
        % Needspace alone cannot see the eventual column boundary.  Forbid the
        % vertical break below the heading and the first line break of the
        % explanation as well; later lines and paragraphs remain breakable.
        \nobreak\smallskip\nobreak\noindent
        \clubpenalty=10000
        {\NPEEHeadingFace\bfseries
          \NPEEAnswerKeySolutionLabel\NPEELabelSeparator}\,\ignorespaces
    \fi
  \fi}
\newcommand{\NPEEAnswerKeySolutionEnd}{%
  \ifnum\NPEEAnswerKeySolutionNesting>0\relax
    \global\advance\NPEEAnswerKeySolutionNesting by -1\relax
  \else
    \ifNPEEAnswerKeySolutionActive
      \par
      \endgroup
      \global\NPEEAnswerKeySolutionActivefalse
    \fi
  \fi}
\NewDocumentCommand{\NPEEAnswerKeyRow}{m m O{}}{%
  \NPEEAnswerKeyRequireActive
  \ifNPEEAnswerKeyActive
    \par\addvspace{\NPEEAnswerKeyGap}\noindent
    \begingroup\NPEEBodyFace
      \hangindent=\dimexpr\NPEEAnswerKeyNumberWidth+\NPEEAnswerKeyPointsWidth+1.4em\relax
      \hangafter=1
      \makebox[\NPEEAnswerKeyNumberWidth][l]{\textup{#1.}}%
      \makebox[\NPEEAnswerKeyPointsWidth][r]{\NPEEAnswerKeyPointLabel{#3}}%
      \hspace{.7em}\textup{\NPEEAnswerKeyAnswerLabel\NPEELabelSeparator}\,#2\par
    \endgroup
  \fi}
\NewDocumentCommand{\NPEEAnswerKeySolution}{O{} m +m}{%
  \ifNPEEAnswerKeyActive
    \ifNPEEAnswerKeySolutionActive
      \NPEEWarningNoLine{npee-math-exam}{Nested answer-key solution ignored}%
    \else
      \NPEEAnswerKeySolutionStart[#1]{#2}%
      #3\NPEEAnswerKeySolutionEnd
    \fi
  \else
    \NPEEAnswerKeyRequireActive
  \fi}
\NewDocumentEnvironment{NPEEAnswerKeySolutionBlock}{O{}m}{%
  \NPEEAnswerKeySolutionStart[#1]{#2}%
}{%
  \NPEEAnswerKeySolutionEnd
}




% -----------------------------------------------------------------------------
% Feature section: structured question API
% -----------------------------------------------------------------------------

\RequirePackage{tasks}

% -----------------------------------------------------------------------------
% Feature section: question figures
% -----------------------------------------------------------------------------

% Figures are ordinary in-flow material.  The class deliberately does not use
% LaTeX floats here: an attached diagram belongs to the question that
% references it, so it must not migrate to a later column or page.  Resource
% paths and captions are supplied by the question bank; these defaults only
% describe the reusable rendering contract.
\newif\ifNPEEFigureInline
\newif\ifNPEEFigureKeepAspectRatio
\NPEEFigureInlinefalse
\NPEEFigureKeepAspectRatiotrue
\newcommand{\NPEEFigureWidth}{\linewidth}
\newcommand{\NPEEFigureHeight}{}
\newcommand{\NPEEFigureMaxHeight}{.30\textheight}
\newcommand{\NPEEFigureAlignment}{center}
\newcommand{\NPEEFigureBeforeSkip}{.8mm}
\newcommand{\NPEEFigureAfterSkip}{.8mm}
\newcommand{\NPEEFigureCaption}{}
\newcommand{\NPEEFigureAltText}{}
\newcommand{\NPEEFigureLabel}{}
\newcommand{\NPEEFigureExtraOptions}{}
\newcommand{\NPEEFigureCaptionFace}{\NPEEBodyFace\fontsize{9pt}{11pt}\selectfont}

\newcommand{\NPEEResetFigureOptions}{%
  \NPEEFigureInlinefalse
  \NPEEFigureKeepAspectRatiotrue
  \renewcommand{\NPEEFigureWidth}{\linewidth}%
  \renewcommand{\NPEEFigureHeight}{}%
  \renewcommand{\NPEEFigureMaxHeight}{.30\textheight}%
  \renewcommand{\NPEEFigureAlignment}{center}%
  \renewcommand{\NPEEFigureBeforeSkip}{.8mm}%
  \renewcommand{\NPEEFigureAfterSkip}{.8mm}%
  \renewcommand{\NPEEFigureCaption}{}%
  \renewcommand{\NPEEFigureAltText}{}%
  \renewcommand{\NPEEFigureLabel}{}%
  \renewcommand{\NPEEFigureExtraOptions}{}%
}

\pgfkeys{/npee/figure/.is family,/npee/figure,
  width/.code={\renewcommand{\NPEEFigureWidth}{#1}},
  height/.code={%
    \edef\NPEEFigureHeightValue{#1}%
    \ifnum\pdfstrcmp{\NPEEFigureHeightValue}{none}=0
      \renewcommand{\NPEEFigureHeight}{}%
    \else
      \renewcommand{\NPEEFigureHeight}{#1}%
    \fi},
  max-height/.code={%
    \edef\NPEEFigureMaxHeightValue{#1}%
    \ifnum\pdfstrcmp{\NPEEFigureMaxHeightValue}{none}=0
      \renewcommand{\NPEEFigureMaxHeight}{}%
    \else
      \renewcommand{\NPEEFigureMaxHeight}{#1}%
    \fi},
  align/.code={%
    \edef\NPEEFigureAlignmentValue{#1}%
    \ifnum\pdfstrcmp{\NPEEFigureAlignmentValue}{left}=0
      \renewcommand{\NPEEFigureAlignment}{left}%
    \else\ifnum\pdfstrcmp{\NPEEFigureAlignmentValue}{right}=0
      \renewcommand{\NPEEFigureAlignment}{right}%
    \else\ifnum\pdfstrcmp{\NPEEFigureAlignmentValue}{center}=0
      \renewcommand{\NPEEFigureAlignment}{center}%
    \else
      \NPEEWarning{npee-math-exam}{Unknown figure alignment `#1'; using center}%
      \renewcommand{\NPEEFigureAlignment}{center}%
    \fi\fi\fi},
  display/.code={%
    \edef\NPEEFigureDisplayValue{#1}%
    \ifnum\pdfstrcmp{\NPEEFigureDisplayValue}{inline}=0
      \NPEEFigureInlinetrue
    \else\ifnum\pdfstrcmp{\NPEEFigureDisplayValue}{block}=0
      \NPEEFigureInlinefalse
    \else
      \NPEEWarning{npee-math-exam}{Unknown figure display `#1'; using block}%
      \NPEEFigureInlinefalse
    \fi\fi},
  keep-aspect-ratio/.is if=NPEEFigureKeepAspectRatio,
  before-skip/.code={\renewcommand{\NPEEFigureBeforeSkip}{#1}},
  after-skip/.code={\renewcommand{\NPEEFigureAfterSkip}{#1}},
  caption/.code={\renewcommand{\NPEEFigureCaption}{#1}},
  alt/.code={\renewcommand{\NPEEFigureAltText}{#1}},
  label/.code={\renewcommand{\NPEEFigureLabel}{#1}},
  options/.code={\renewcommand{\NPEEFigureExtraOptions}{#1}},
  caption-font/.code={\renewcommand{\NPEEFigureCaptionFace}{#1}},
  .unknown/.code={\NPEEWarning{npee-math-exam}{Unknown figure key `\pgfkeyscurrentname' ignored}}
}

\newcommand{\NPEEFigureSetup}[1]{%
  \NPEEResetFigureOptions
  \pgfkeys{/npee/figure/.cd,#1}}

\newcommand{\NPEEApplyFigureAlignment}{%
  \ifnum\pdfstrcmp{\NPEEFigureAlignment}{left}=0
    \raggedright
  \else\ifnum\pdfstrcmp{\NPEEFigureAlignment}{right}=0
    \raggedleft
  \else
    \centering
  \fi\fi}

% Keep both width and height as upper bounds when max-height is configured.
% An explicit height takes precedence over max-height; `none' disables that
% bound.  The optional `options' key is intentionally passed through to
% graphicx for crops or rotations that are part of an audited asset record.
% Keep the empty-options branches explicit: a trailing comma is interpreted as
% an empty key by graphicx/keyval on some TeX releases.
\newcommand{\NPEEIncludeFigureGraphicsNoExtra}[1]{%
  \ifNPEEFigureKeepAspectRatio
    \ifx\NPEEFigureHeight\@empty
      \ifx\NPEEFigureMaxHeight\@empty
        \includegraphics[keepaspectratio,width=\NPEEFigureWidth]{#1}%
      \else
        \includegraphics[keepaspectratio,width=\NPEEFigureWidth,height=\NPEEFigureMaxHeight]{#1}%
      \fi
    \else
      \includegraphics[keepaspectratio,width=\NPEEFigureWidth,height=\NPEEFigureHeight]{#1}%
    \fi
  \else
    \ifx\NPEEFigureHeight\@empty
      \ifx\NPEEFigureMaxHeight\@empty
        \includegraphics[width=\NPEEFigureWidth]{#1}%
      \else
        \includegraphics[width=\NPEEFigureWidth,height=\NPEEFigureMaxHeight]{#1}%
      \fi
    \else
      \includegraphics[width=\NPEEFigureWidth,height=\NPEEFigureHeight]{#1}%
    \fi
  \fi}
\newcommand{\NPEEIncludeFigureGraphics}[1]{%
  \ifx\NPEEFigureExtraOptions\@empty
    \NPEEIncludeFigureGraphicsNoExtra{#1}%
  \else
    \ifNPEEFigureKeepAspectRatio
      \ifx\NPEEFigureHeight\@empty
        \ifx\NPEEFigureMaxHeight\@empty
          \includegraphics[keepaspectratio,width=\NPEEFigureWidth,\NPEEFigureExtraOptions]{#1}%
        \else
          \includegraphics[keepaspectratio,width=\NPEEFigureWidth,height=\NPEEFigureMaxHeight,\NPEEFigureExtraOptions]{#1}%
        \fi
      \else
        \includegraphics[keepaspectratio,width=\NPEEFigureWidth,height=\NPEEFigureHeight,\NPEEFigureExtraOptions]{#1}%
      \fi
    \else
      \ifx\NPEEFigureHeight\@empty
        \ifx\NPEEFigureMaxHeight\@empty
          \includegraphics[width=\NPEEFigureWidth,\NPEEFigureExtraOptions]{#1}%
        \else
          \includegraphics[width=\NPEEFigureWidth,height=\NPEEFigureMaxHeight,\NPEEFigureExtraOptions]{#1}%
        \fi
      \else
        \includegraphics[width=\NPEEFigureWidth,height=\NPEEFigureHeight,\NPEEFigureExtraOptions]{#1}%
      \fi
    \fi
  \fi}

\newcommand{\NPEEWithFigureAlt}[1]{%
  \ifx\NPEEFigureAltText\@empty
    #1%
  \else
    % hyperref's tooltip becomes an accessible description when supported;
    % the image remains unchanged for engines without that optional command.
    \ifcsname pdftooltip\endcsname
      \pdftooltip{#1}{\NPEEFigureAltText}%
    \else
      #1%
    \fi
  \fi}

\NewDocumentEnvironment{NPEEFigure}{O{}m}{%
  \begingroup
    \NPEEFigureSetup{#1}%
    \ifNPEEFigureInline
      \leavevmode\NPEEWithFigureAlt{\NPEEIncludeFigureGraphics{#2}}%
    \else
      \par\addvspace{\NPEEFigureBeforeSkip}%
      \noindent\NPEEApplyFigureAlignment
      \NPEEWithFigureAlt{\NPEEIncludeFigureGraphics{#2}}\par
      \ifx\NPEEFigureCaption\@empty\else
        \vspace{.35mm}{\NPEEFigureCaptionFace\NPEEFigureCaption\par}%
      \fi
      \ifx\NPEEFigureLabel\@empty\else\label{\NPEEFigureLabel}\fi
      \vspace{\NPEEFigureAfterSkip}%
    \fi
}{%
    \par
  \endgroup}
\NewDocumentCommand{\NPEEIncludeFigure}{O{}m}{%
  \begin{NPEEFigure}[#1]{#2}\end{NPEEFigure}}

% Document-level defaults are optional; per-figure keys above always take
% precedence and reset at the beginning of each figure.
\NPEEDeclareSetupKeys{
  figure/default-width/.code={\renewcommand{\NPEEFigureWidth}{#1}},
  figure/max-height/.code={\renewcommand{\NPEEFigureMaxHeight}{#1}},
  figure/before-skip/.code={\renewcommand{\NPEEFigureBeforeSkip}{#1}},
  figure/after-skip/.code={\renewcommand{\NPEEFigureAfterSkip}{#1}},
  figure/caption-font/.code={\renewcommand{\NPEEFigureCaptionFace}{#1}}
}

\newcommand{\NPEEQuestionID}{}
\newcommand{\NPEEQuestionType}{}
\newcommand{\NPEEQuestionPointsValue}{}
\newcommand{\NPEEQuestionShowPointsMode}{auto}
\newif\ifNPEEQuestionShowPoints
\NPEEQuestionShowPointsfalse

\pgfkeys{/npee/question/.is family,/npee/question,
  id/.store in=\NPEEQuestionID,
  type/.store in=\NPEEQuestionType,
  points/.code={\def\NPEEQuestionPointsValue{#1}},
  show-points/.code={\def\NPEEQuestionShowPointsMode{#1}},
  .unknown/.code={\NPEEWarning{npee-math-exam}{Unknown question key `\pgfkeyscurrentname' ignored}}
}
\newcommand{\NPEEResolveQuestionPointVisibility}{%
  \NPEEQuestionShowPointsfalse
  \def\NPEEQuestionAutoMode{auto}%
  \def\NPEEQuestionTrueMode{true}%
  \def\NPEEQuestionFalseMode{false}%
  \ifx\NPEEQuestionShowPointsMode\NPEEQuestionAutoMode
    \ifx\NPEEQuestionPointsValue\@empty\else
      \NPEEQuestionShowPointstrue
    \fi
  \else\ifx\NPEEQuestionShowPointsMode\NPEEQuestionTrueMode
    \NPEEQuestionShowPointstrue
  \else\ifx\NPEEQuestionShowPointsMode\NPEEQuestionFalseMode
    \relax
  \else
    \NPEEWarning{npee-math-exam}{Unknown show-points value `\NPEEQuestionShowPointsMode'; using auto}%
    \ifx\NPEEQuestionPointsValue\@empty\else
      \NPEEQuestionShowPointstrue
    \fi
  \fi\fi\fi}
\newcommand{\NPEEQuestionSetup}[1]{%
  \def\NPEEQuestionID{}%
  \def\NPEEQuestionType{}%
  \def\NPEEQuestionPointsValue{}%
  \renewcommand{\NPEEQuestionShowPointsMode}{auto}%
  % Expand one indirection before pgfkeys parses the list.  The automatic
  % solution environment stores its document-level id in a macro so the
  % source remains content-only; without this expansion pgfkeys treats the
  % macro name itself as an unknown key.
  \edef\NPEEExpandedQuestionKeys{/npee/question/.cd,#1}%
  \expandafter\pgfkeys\expandafter{\NPEEExpandedQuestionKeys}}

\newenvironment{ExamQuestion}[1][]{%
  \begingroup
  \NPEEQuestionSetup{#1}%
  \begin{NPEEExamQuestion}%
  \ifx\NPEEQuestionID\@empty\else
    \label{exam.question.\arabic{npeeexampaper}.\NPEEQuestionID}%
  \fi
  \NPEEResolveQuestionPointVisibility
  \ifx\NPEEQuestionPointsValue\@empty
    \ifNPEEQuestionShowPoints
      \NPEEWarning{npee-math-exam}{show-points=true requires a points value; score label omitted}%
    \fi
  \else
    \NPEERegisterQuestionPoints{\NPEEQuestionPointsValue}%
    \ifNPEEQuestionShowPoints
      \NPEEPrintQuestionPoints{\NPEEQuestionPointsValue}%
    \fi
  \fi
}{%
  \end{NPEEExamQuestion}%
  \endgroup}
\newenvironment{ExamChoiceQuestion}[1][]{%
  \begin{ExamQuestion}[type=choice,#1]}{\end{ExamQuestion}}
\newenvironment{ExamFillQuestion}[1][]{%
  \begin{ExamQuestion}[type=fillin,#1]}{\end{ExamQuestion}}
% The score is optional for imported records whose source does not print a
% reliable value.  The public form is `[question-keys]{points}`; height is an
% internal layout decision.  The old `[height][question-keys]{points}` form
% remains accepted, as does the historical single `[height]{points}` form.
\newif\ifNPEESolutionLegacyArguments
\NPEESolutionLegacyArgumentsfalse
\newcommand{\NPEEConfigureSolutionArguments}[2]{%
  \NPEESolutionLegacyArgumentsfalse
  \NPEESolutionCellActivefalse
  \def\NPEESolutionKeys{}%
  \def\NPEESolutionHeightSpec{auto}%
  \IfNoValueTF{#2}{%
    \if\relax\detokenize{#1}\relax
    \else
      % A single optional argument containing a key assignment is the new
      % source form; a bare dimension/macro is retained as a legacy height.
      \in@{=}{#1}%
      \ifin@
        \def\NPEESolutionKeys{#1}%
      \else
        \NPEESolutionLegacyArgumentstrue
        \def\NPEESolutionHeightSpec{#1}%
      \fi
    \fi
  }{%
    \NPEESolutionLegacyArgumentstrue
    \def\NPEESolutionHeightSpec{#1}%
    \def\NPEESolutionKeys{#2}%
  }}

\NewDocumentEnvironment{ExamSolutionQuestion}{O{}og}{%
  % A spread automatic cell may have queued a logical-column transition after
  % the previous response.  Consume it before entering the structural
  % conditionals below; output routines must not run with those conditionals
  % open.  This must also happen before this environment creates its local
  % group: multicols may execute its output routine while processing the
  % column break, and that routine must see the surrounding document group
  % rather than an unfinished solution-question group.
  \NPEEConsumeAnswerBreak
  \begingroup
  \NPEEConfigureSolutionArguments{#1}{#2}%
  \ifNPEESolutionLegacyArguments
    \NPEEWarnLegacySolutionHeight
    \stepcounter{npeesolutionquestion}%
    \def\NPEESolutionAnswerHeight{\NPEESolutionHeightSpec}%
  \else
    \NPEEPrepareAutomaticSolutionCell
  \fi
  % Select the cell environment while conditionals are closed, then execute
  % it.  This prevents a multicols output routine from inheriting the
  % implementation branch that selected the cell.
  \def\NPEESolutionCellBegin{}%
  % Decide both halves of the structural cell contract before opening the
  % minipage.  A minipage may invoke the multicols output routine when it is
  % closed; definitions made from inside that group would then be restored
  % before the environment's end code can use them.
  \def\NPEESolutionCellEnd{}%
  \def\NPEESolutionCellGapAction{}%
  \ifNPEESolutionCellActive
    \ifNPEESolutionHalfCell
      \def\NPEESolutionCellBegin{\NPEEStartAnswerHalfCell}%
      \def\NPEESolutionCellEnd{\NPEEFinishAnswerCell}%
      \ifnum\value{npeesolutionquestion}<\NPEESolutionPairCount
        \def\NPEESolutionCellGapAction{\NPEEAnswerCellGap}%
      \fi
    \else
      \def\NPEESolutionCellBegin{\NPEEStartAnswerFullCell}%
      \def\NPEESolutionCellEnd{\NPEEFinishAnswerCell}%
    \fi
  \fi
  \NPEESolutionCellBegin
  % Resolve the optional score before opening ExamQuestion.  Keeping the
  % xparse conditional out of the question body is essential for spread flow: a
  % fixed response cell may invoke multicols' output routine while the body
  % is being boxed.
  \def\NPEESolutionQuestionOptions{type=solution,show-points=false,\NPEESolutionKeys}%
  \IfNoValueTF{#3}{}{\def\NPEESolutionQuestionOptions{type=solution,points=#3,\NPEESolutionKeys}}%
  \begin{ExamQuestion}[\NPEESolutionQuestionOptions]}{%
  % Structural answer cells already contain their complete response slot.
  % Calling \NPEEAnswerSpace here would reintroduce a hidden height fallback
  % for natural/spread flows, so reserve space only for the legacy explicit form.
  % Resolve this compatibility branch before closing the question/minipage.
  % The minipage terminator may enter a multicols output routine; leaving the
  % conditional open across that terminator corrupts TeX's conditional stack.
  \def\NPEELegacyAnswerSpaceAction{}%
  \ifNPEESolutionLegacyArguments
    \def\NPEELegacyAnswerSpaceAction{\NPEEAnswerSpace{\NPEESolutionAnswerHeight}}%
  \fi
  \NPEELegacyAnswerSpaceAction
  \end{ExamQuestion}%
  \NPEESolutionCellEnd
  \NPEESolutionCellGapAction
  \NPEEQueueAutomaticSolutionBreak
  \endgroup}

% Captured solutions occupy no space in student mode and remain naturally
% breaking in teacher/key mode.
\NewDocumentEnvironment{ExamSolution}{O{\NPEEAnswerLabel}+b}{%
  \ifNPEEAnswerMode
    \par\addvspace{1.2mm}\noindent
    {\NPEEHeadingFace\bfseries #1}\par\noindent #2\par
  \fi
}{}

\newcommand{\NPEEChoiceListColumns}{1}
\newcommand{\NPEEChoiceListLabelSep}{.6em}
\newcommand{\NPEEChoiceListItemSep}{.35em}
\newcommand{\NPEEChoiceListColumnSep}{1.2em}
\newcommand{\NPEEChoiceListItemIndent}{2em}
\newcommand{\NPEEChoiceListLabelWidth}{1.25em}
\newcommand{\NPEEChoiceListLabelAlign}{left}
\newcommand{\NPEEChoiceListBeforeSkip}{.35em}
\newcommand{\NPEEChoiceListAfterSkip}{0pt}
\pgfkeys{/npee/choices/.is family,/npee/choices,
  columns/.code={\def\NPEEChoiceListColumns{#1}},
  label-sep/.code={\renewcommand{\NPEEChoiceListLabelSep}{#1}},
  item-sep/.code={\renewcommand{\NPEEChoiceListItemSep}{#1}},
  column-sep/.code={\renewcommand{\NPEEChoiceListColumnSep}{#1}},
  item-indent/.code={\renewcommand{\NPEEChoiceListItemIndent}{#1}},
  label-width/.code={\renewcommand{\NPEEChoiceListLabelWidth}{#1}},
  label-align/.code={\renewcommand{\NPEEChoiceListLabelAlign}{#1}},
  before-skip/.code={\renewcommand{\NPEEChoiceListBeforeSkip}{#1}},
  after-skip/.code={\renewcommand{\NPEEChoiceListAfterSkip}{#1}},
  .unknown/.code={\NPEEWarning{npee-math-exam}{Unknown choices key `\pgfkeyscurrentname' ignored}}
}
\newcommand{\ExamSetChoices}[1]{\pgfkeys{/npee/choices/.cd,#1}}
\NewTasksEnvironment[
  style=alphabetize,
  label=\Alph*.,
  label-format=\textup,
  label-align=\NPEEChoiceListLabelAlign,
  item-indent=\NPEEChoiceListItemIndent,
  label-width=\NPEEChoiceListLabelWidth,
  label-offset=\NPEEChoiceListLabelSep,
  column-sep=\NPEEChoiceListColumnSep,
  before-skip=\NPEEChoiceListBeforeSkip,
  after-skip=\NPEEChoiceListAfterSkip,
  after-item-skip=\NPEEChoiceListItemSep
]{NPEEChoiceTasks}[\item](1)
\newcommand{\NPEEResolveChoiceListColumns}{%
  \def\NPEEChoiceListResolvedColumns{1}%
  \def\NPEEChoiceListValid{0}%
  \ifnum\pdfstrcmp{\NPEEChoiceListColumns}{1}=0
    \def\NPEEChoiceListValid{1}%
  \fi
  \ifnum\pdfstrcmp{\NPEEChoiceListColumns}{2}=0
    \def\NPEEChoiceListResolvedColumns{2}%
    \def\NPEEChoiceListValid{1}%
  \fi
  \ifnum\pdfstrcmp{\NPEEChoiceListColumns}{4}=0
    \def\NPEEChoiceListResolvedColumns{4}%
    \def\NPEEChoiceListValid{1}%
  \fi
  \ifnum\NPEEChoiceListValid=0
    \NPEEWarning{npee-math-exam}{Choice columns `\NPEEChoiceListColumns' is invalid; using 1}%
  \fi}
\NewDocumentEnvironment{ExamChoiceList}{O{}+b}{%
  \begingroup
  \pgfkeys{/npee/choices/.cd,#1}%
  \NPEEResolveChoiceListColumns
  \begin{NPEEChoiceTasks}(\NPEEChoiceListResolvedColumns)
    #2
  \end{NPEEChoiceTasks}%
  \endgroup
}{}




% -----------------------------------------------------------------------------
% Feature section: public compatibility aliases
% -----------------------------------------------------------------------------

\providecommand{\ExamCircledNumber}{\NPEECircledDigit}
\providecommand{\ExamCircledItem}{\NPEECircledItem}
\providecommand{\ExamCircledItemRef}{\NPEECircledItemRef}
\providecommand{\ExamCircledStatement}{\NPEECircledStatement}
\providecommand{\ExamStatementMarker}{\NPEEStatementMarker}
\providecommand{\ExamStatement}{\NPEEStatement}
\providecommand{\ExamStatements}{\NPEEStatements}
\providecommand{\ExamAnswer}{\NPEEAnswer}
\providecommand{\ExamShowSolutions}{\NPEEEnableAnswers}
\providecommand{\ExamHideSolutions}{\NPEEDisableAnswers}
\NewDocumentCommand{\ExamQuestionRef}{O{\arabic{npeeexampaper}}m}{%
  \ref{exam.question.#1.#2}}

% Neutral public aliases.  The historical NPEE names remain the canonical
% implementation API; these aliases make small independent exam projects
% readable without coupling their source to the publisher namespace.
\NewDocumentCommand{\ExamPaperSetup}{m}{\NPEESetPaperInfo{#1}}
\NewDocumentCommand{\ExamPaperStart}{O{}}{%
  \NPEESetPaperInfo{#1}%
  \NPEEExamPaperStart}
\providecommand{\ExamPaperEnd}{\NPEEExamPaperEnd}
\providecommand{\ExamBeginBookBody}{\NPEEBeginBookBody}
\providecommand{\ExamBeginAppendix}{\NPEEBeginAppendix}
\providecommand{\ExamBackMatterStart}{\NPEEBackMatterStart}
\NewDocumentEnvironment{ExamPaper}{O{}}{%
  \NPEESetPaperInfo{#1}%
  \NPEEExamPaperStart
}{%
  \NPEEExamPaperEnd}
% -----------------------------------------------------------------------------
% Feature section: collection composition API
% -----------------------------------------------------------------------------

% A collection is deliberately a document-level concept.  The class only
% supplies the lifecycle needed to compose an arbitrary number of papers; a
% manifest decides which source files belong to the collection.  This keeps
% the same class usable for a single paper, a short mock set, or a book with
% dozens of papers.
\newif\ifNPEECollectionActive
\NPEECollectionActivefalse

\newcommand{\NPEECollectionStart}[1]{%
  \ifNPEECollectionActive
    \NPEEWarningNoLine{npee-math-exam}{CollectionStart called while a collection is already active; ignored}%
  \else
    \ifNPEEExamActive\NPEEExamPaperEnd\fi
    \if\relax\detokenize{#1}\relax\else\NPEESetup{#1}\fi
    \NPEEBeginBookBody
    \global\NPEECollectionActivetrue
  \fi}

\newcommand{\NPEECollectionEnd}{%
  \ifNPEECollectionActive
    \ifNPEEExamActive\NPEEExamPaperEnd\fi
    \global\NPEECollectionActivefalse
  \else
    \NPEEWarningNoLine{npee-math-exam}{CollectionEnd called without an active collection; ignored}%
  \fi}

% Collection-level navigation belongs beside the composition lifecycle.  A
% project supplies the visible title and may call these commands between any
% number of imported papers; no publication identity is assumed here.
\newcommand{\NPEEContentsTitle}{目录}
\newcommand{\NPEESetContentsTitle}[1]{\renewcommand{\NPEEContentsTitle}{#1}}
\newcommand{\NPEESetCollectionContentsEntries}[2]{%
  \ifnum#1=1\relax
    \global\NPEECollectionGroupContentsEnabledtrue
  \else
    \global\NPEECollectionGroupContentsEnabledfalse
  \fi
  \ifnum#2=1\relax
    \global\NPEECollectionPaperContentsEnabledtrue
  \else
    \global\NPEECollectionPaperContentsEnabledfalse
  \fi}
\newcommand{\NPEECollectionContents}{%
  \global\NPEECollectionContentsEnabledtrue
  \clearpage
  \NPEEBookmark{\NPEEContentsTitle}{collection-contents}%
  \NPEECollectionContentsBeginColumns
  \begingroup
    \renewcommand{\contentsname}{\NPEEContentsTitle}%
    \NPEEBodyFace\NPEEApplyBodyStyle\tableofcontents
  \endgroup
  \NPEECollectionContentsEndColumns
  \clearpage}

\newcounter{npeecollectionsection}
\newcommand{\NPEECollectionSectionTitleSize}{16pt}
\newcommand{\NPEECollectionSectionTitleLineHeight}{22pt}
\newcommand{\NPEESetCollectionSectionStyle}[2]{%
  \renewcommand{\NPEECollectionSectionTitleSize}{#1}%
  \renewcommand{\NPEECollectionSectionTitleLineHeight}{#2}}
\NPEEDeclareSetupKeys{
  collection/contents-title/.code={\NPEESetContentsTitle{#1}},
  collection/section-font-size/.code={\renewcommand{\NPEECollectionSectionTitleSize}{#1}},
  collection/section-line-height/.code={\renewcommand{\NPEECollectionSectionTitleLineHeight}{#1}}
}
\NewDocumentCommand{\NPEECollectionSection}{O{}m}{%
  \ifNPEEExamActive
    \NPEEExamPaperEnd
  \else
    \NPEEExamEndColumns\clearpage
  \fi
  \stepcounter{npeecollectionsection}%
  \def\NPEECollectionSectionKey{collection-section-\arabic{npeecollectionsection}}%
  \if\relax\detokenize{#1}\relax\else
    \edef\NPEECollectionSectionKey{#1}%
  \fi
  \NPEEBookmark{#2}{\NPEECollectionSectionKey}%
  \ifNPEECollectionContentsEnabled
    \ifNPEECollectionGroupContentsEnabled
       \NPEEAddContentsEntry{section}{#2}%
    \fi
  \fi
  \thispagestyle{empty}%
  \vspace*{\fill}%
  \begin{center}
    {\NPEEHeadingFace\fontsize{\NPEECollectionSectionTitleSize}{\NPEECollectionSectionTitleLineHeight}\selectfont #2\par}
  \end{center}%
  \vspace*{\fill}\clearpage}

% A composition may need a semantic group in the table of contents and PDF
% outline without spending a visible title page on that group.  This marker is
% intentionally side-effect free with respect to pagination.
\NewDocumentCommand{\NPEECollectionSectionMarker}{O{}m}{%
  \def\NPEECollectionSectionKey{collection-section-marker-\arabic{npeecollectionsection}}%
  \if\relax\detokenize{#1}\relax\else
    \edef\NPEECollectionSectionKey{#1}%
  \fi
  \NPEEBookmark{#2}{\NPEECollectionSectionKey}%
  \ifNPEECollectionContentsEnabled
    \ifNPEECollectionGroupContentsEnabled
       \NPEEAddContentsEntry{section}{#2}%
    \fi
  \fi}

% Body-fragment import.  The imported file must contain only sections and
% questions: this command owns both paper boundaries, so it is safe to repeat
% it any number of times in a manifest.  The optional bookmark-title and
% bookmark-key keys configure this one paper and are reset by the normal paper
% lifecycle (they are registered in the /npee/paper key family).
\NewDocumentCommand{\NPEEInputPaper}{O{}m}{%
  \ifNPEEExamActive\NPEEExamPaperEnd\fi
  \NPEESetPaperInfo{#1}%
  \NPEEExamPaperStart
  \input{#2}%
  \NPEEExamPaperEnd}

% Compatibility import for the historical source files in which the file
% itself calls \NPEEExamPaperStart (and the next file closes the previous
% paper).  New bank entries should prefer the body-fragment contract above,
% but this bridge lets an existing collection be rearranged without editing
% every legacy paper at once.
\NewDocumentCommand{\NPEEInputLegacyPaper}{m}{%
  \ifNPEEExamActive\NPEEExamPaperEnd\fi
  \input{#1}}

% Convenience form for a list of body fragments that use the default paper
% metadata.  Per-paper bookmarks or other metadata should use explicit
% \NPEEInputPaper lines in the manifest instead.
\newcommand{\NPEEInputPaperList}[1]{%
  \@for\NPEEListItem:=#1\do{\NPEEInputPaper{\NPEEListItem}}}

\NewDocumentEnvironment{ExamCollection}{O{}}{%
  \begingroup
  \NPEECollectionStart{#1}%
}{%
  \NPEECollectionEnd
  \endgroup
}

\NewDocumentCommand{\ExamCollectionStart}{O{}}{\NPEECollectionStart{#1}}
\providecommand{\ExamCollectionEnd}{\NPEECollectionEnd}
\providecommand{\ExamInputPaper}{\NPEEInputPaper}
\providecommand{\ExamInputLegacyPaper}{\NPEEInputLegacyPaper}
\providecommand{\ExamInputPaperList}{\NPEEInputPaperList}
\providecommand{\ExamCollectionContents}{\NPEECollectionContents}
\providecommand{\ExamCollectionSection}{\NPEECollectionSection}
\providecommand{\ExamCollectionSectionMarker}{\NPEECollectionSectionMarker}

\providecommand{\ExamSection}{\NPEEExamSection}
\providecommand{\ExamSectionContinue}{\NPEEExamSectionContinue}
\providecommand{\ExamSolutionHere}{\NPEEExamSolutionHere}
\providecommand{\ExamSelection}{\NPEESelection}
\providecommand{\ExamBlank}{\NPEEBlank}
\providecommand{\ExamChoices}{\NPEEChoices}
\providecommand{\ExamChoicesOneLine}{\NPEEChoicesOneLine}
\providecommand{\ExamChoicesTwoByTwo}{\NPEEChoicesTwoByTwo}
\providecommand{\ExamChoicesOnePerLine}{\NPEEChoicesOnePerLine}
\providecommand{\ExamGraphicChoices}{\NPEEGraphicChoices}
\providecommand{\ExamQuestionPoints}{\NPEEQuestionPoints}
\providecommand{\ExamTotalPoints}{\NPEETotalPoints}
\providecommand{\ExamQuestionContinuation}{\NPEEQuestionContinuation}
\providecommand{\ExamInlineMath}{\NPEEInlineMath}
\providecommand{\ExamIncludeFigure}{\NPEEIncludeFigure}
\providecommand{\ExamIncludeTikz}{\NPEEIncludeTikz}
\providecommand{\ExamChoiceGraphic}{\NPEEChoiceGraphic}
\NewDocumentEnvironment{ExamFigure}{O{}m}{%
  \begin{NPEEFigure}[#1]{#2}%
}{%
  \end{NPEEFigure}%
}
\providecommand{\ExamAnswerKeyStart}{\NPEEAnswerKeyStart}
\providecommand{\ExamAnswerKeyEnd}{\NPEEAnswerKeyEnd}
\providecommand{\ExamAnswerKeySection}{\NPEEAnswerKeySection}
\providecommand{\ExamAnswerKeyRow}{\NPEEAnswerKeyRow}
\providecommand{\ExamAnswerKeySolution}{\NPEEAnswerKeySolution}
\providecommand{\ExamAnswerKeySolutionStart}{\NPEEAnswerKeySolutionStart}
\providecommand{\ExamAnswerKeySolutionEnd}{\NPEEAnswerKeySolutionEnd}
\providecommand{\ExamAnswerKeySpreadBreak}{\NPEEAnswerKeySpreadBreak}
\providecommand{\ExamSetAnswerKeyTitle}{\NPEESetAnswerKeyTitle}
\providecommand{\ExamSetAnswerKeyLabels}{\NPEESetAnswerKeyLabels}
\providecommand{\ExamSetAnswerKeyWidths}{\NPEESetAnswerKeyWidths}
\providecommand{\ExamSubpart}{\NPEESubpart}
\providecommand{\ExamSubpartRef}{\NPEESubpartRef}
\providecommand{\ExamSetQuestionPointsFormat}{\NPEESetQuestionPointsFormat}
\providecommand{\ExamSetQuestionPointsStyle}{\NPEESetQuestionPointsStyle}
\providecommand{\ExamSetPageCount}{\NPEESetPageCount}
\providecommand{\ExamUseAutomaticPageCount}{\NPEEUseAutomaticPageCount}
\providecommand{\ExamSetSolutionStructure}{\NPEESetSolutionStructure}
\providecommand{\ExamSetSolutionPairCount}{\NPEESetSolutionPairCount}
\providecommand{\ExamSetConfidentialMark}{\NPEESetConfidentialMark}
\providecommand{\ExamShowConfidentialMark}{\NPEEEnableConfidentialMark}
\providecommand{\ExamHideConfidentialMark}{\NPEEDisableConfidentialMark}
\providecommand{\ExamSecurityLevelName}{\NPEESecurityLevelName}
\providecommand{\ExamSetSecurityLevel}{\NPEESetSecurityLevel}
\providecommand{\ExamSetSecurityText}{\NPEESetSecurityText}
\providecommand{\ExamSetSecurityActivationText}{\NPEESetSecurityActivationText}
\providecommand{\ExamSetSecuritySuffix}{\NPEESetSecurityActivationText}
\providecommand{\ExamShowSecurityMark}{\NPEEEnableConfidentialMark}
\providecommand{\ExamHideSecurityMark}{\NPEEDisableConfidentialMark}
\@ifundefined{ExamQuestion}{%
  \newenvironment{ExamQuestion}{\begin{NPEEExamQuestion}}{\end{NPEEExamQuestion}}%
}{}
\@ifundefined{ExamAnswerKeySolutionBlock}{%
  \newenvironment{ExamAnswerKeySolutionBlock}[2][]{%
    \begin{NPEEAnswerKeySolutionBlock}[#1]{#2}%
  }{%
    \end{NPEEAnswerKeySolutionBlock}%
  }%
}{}




% Mathematical operator aliases for sources that prefer the neutral Exam API.
\providecommand{\ExamIntegralWithRegion}{\NPEEIntegralWithRegion}
\providecommand{\ExamDoubleIntegral}{\NPEEDoubleIntegral}
\providecommand{\ExamTripleIntegral}{\NPEETripleIntegral}
\providecommand{\ExamQuadrupleIntegral}{\NPEEQuadrupleIntegral}
\providecommand{\ExamContourIntegral}{\NPEEContourIntegral}
\providecommand{\ExamSurfaceIntegral}{\NPEESurfaceIntegral}
\providecommand{\ExamVolumeContourIntegral}{\NPEEVolumeContourIntegral}
% Re-apply the integral wrappers after all packages and publication profiles have
% finished their math-symbol setup. unicode-math may restore multiple integrals as
% active Unicode math characters during the preamble; the begin-document hook is
% the stable point at which the public operators can be made limit-bearing.
\AtBeginDocument{%
  % Re-apply the limit wrappers after unicode-math has finished installing its
  % operator table.  This keeps inline examination formulas consistent with
  % the integral-region convention below.
  \protected\def\lim{\mathop{\mathrm{lim}}\limits}%
  \protected\def\limsup{\mathop{\mathrm{lim\,sup}}\limits}%
  \protected\def\liminf{\mathop{\mathrm{lim\,inf}}\limits}%
  \protected\def\sum{\mathop{\displaystyle\NPEEOriginalSum}\limits}%
  \protected\def\prod{\mathop{\displaystyle\NPEEOriginalProd}\limits}%
  \protected\def\bigcap{\mathop{\displaystyle\NPEEOriginalBigcap}\limits}%
  \protected\def\bigcup{\mathop{\displaystyle\NPEEOriginalBigcup}\limits}%
  \protected\def\max{\mathop{\mathrm{max}}\limits}%
  \protected\def\min{\mathop{\mathrm{min}}\limits}%
  \protected\def\sup{\mathop{\mathrm{sup}}\limits}%
  \protected\def\inf{\mathop{\mathrm{inf}}\limits}%
  \protected\def\iint{\mathop{\displaystyle\NPEEOriginalDoubleIntegral}\limits}%
  \protected\def\iiint{\mathop{\displaystyle\NPEEOriginalTripleIntegral}\limits}%
  \protected\def\iiiint{\mathop{\displaystyle\NPEEOriginalQuadrupleIntegral}\limits}%
  \protected\def\oint{\mathop{\displaystyle\NPEEOriginalContourIntegral}\limits}%
  \ifcsname oiint\endcsname
    \protected\def\oiint{\mathop{\displaystyle\NPEEOriginalSurfaceIntegral}\limits}%
  \fi
  \ifcsname oiiint\endcsname
    \protected\def\oiiint{\mathop{\displaystyle\NPEEOriginalVolumeContourIntegral}\limits}%
  \fi
}%

\makeatother
\endinput
