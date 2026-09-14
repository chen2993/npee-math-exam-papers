"""Composition rendering: the internals behind :mod:`npee_math_papers.service.tex_builder`.

The builder was one 1500-line module that mixed path resolution, inline-TeX repair,
catalog loading, document parsing, question rendering, page furniture and the
top-level orchestration. Those concerns now live in sibling modules so each can be
read, tested and changed on its own:

======================  =====================================================
Module                  Responsibility
======================  =====================================================
:mod:`~.paths`          repository- vs package-relative path resolution
:mod:`~.text`           single-line strings and TeX-escaped literals
:mod:`~.inline_tex`     inline-TeX validation and historical-write repair
:mod:`~.catalogs`       resolving a composition's papers from the store
:mod:`~.document`       composition document: targets, hooks, watermark, naming
:mod:`~.content`        rendering questions, choices, subparts and figures
:mod:`~.options`        :class:`BuildOptions`
======================  =====================================================

The public entry point stays :func:`npee_math_papers.service.tex_builder.build`, which
orchestrates these pieces.
"""

from __future__ import annotations

__all__: list[str] = []
