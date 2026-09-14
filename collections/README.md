# 组卷包

每套可复现组卷使用一个独立目录：

```text
collections/<collection-id>/
|- composition.json
|- cover-preamble.tex
|- cover.tex
|- hook-before-collection.tex
`- assets/
   `- images-or-other-resources
```

`composition.json` 只保存题库来源、套卷引用、页面选项和资源声明。题面从
`.npee-math-papers/papers/<series>-<year>-<subject>/<paper_no>.yaml` 读取，
套卷由 `composition.json` 的引用（`series_key`/`year`/`subject`/`paper_no`）精确定位；
题库是唯一事实源，组卷包本身不复制题面。

所有可执行 `.tex` 文件，包括封面设计、矢量路径片段与 Hook，都和 `composition.json` 同级。`assets/`
只保存图片、PDF、字体和其他非代码资源。`document.cover.path` 指向 `cover.tex`，它在
`\begin{document}` 后插入，因而可以
使用任意正文级 LaTeX、TikZ 和包内资源。若封面需要额外宏包或预导言宏定义，使用可选的
`document.cover.preamble` 指向 `cover-preamble.tex`；该文件在文档开始前输入。资源路径
必须相对组卷包，不允许绝对路径或 `..`。

`document.hooks` 支持六个注入点：`preamble`、`before_collection`、`before_group`、
`after_group`、`after_collection` 和 `before_end_document`。每个值都是同级 `.tex` 文件名数组；
组级 Hook 可读取 `\NPEEHookGroupId` 与 `\NPEEHookGroupTitle`。生成器为每个组卷包自动设置
`\input@path` 和 `\graphicspath` 到该包及其 `assets/` 目录。封面源码必须自行结束页面，通常以
`\clearpage` 或 `\includepdf` 的页面命令完成。编译禁用 shell escape；组卷包仍应只包含可信的
LaTeX 源码。

## 三科同组合

当数学一、二、三需要使用相同的年份、系列和套号组合时，把每个套卷引用的 `subject` 写成
`"$subject"`，并在 `compile.subjects` 中列出目标科目。例如：

```json
"papers": [{"year": 2023, "subject": "$subject", "series_key": "zhangyu8", "paper_no": 1}],
"compile": {"subjects": ["math1", "math2", "math3"]}
```

构建器会为每个科目单独解析题面、设置对应的科目名称和代码，并生成独立 PDF。若任一目标
科目缺少对应套卷，整个构建会失败，不会悄悄混用其他科目的题面。
