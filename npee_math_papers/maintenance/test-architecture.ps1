[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$Package = 'npee_math_papers'

function Resolve-Repo([string]$Path) {
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $RepositoryRoot $Path))
}

function Require-File([string]$RelativePath) {
  $Path = Resolve-Repo $RelativePath
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing active file: $RelativePath" }
}

function Require-Directory([string]$RelativePath) {
  $Path = Resolve-Repo $RelativePath
  if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Missing active directory: $RelativePath" }
}

# --- core library -----------------------------------------------------------
foreach ($File in @(
  "$Package/__init__.py",
  "$Package/__main__.py",
  "$Package/core/__init__.py",
  "$Package/core/canonical.py",
  "$Package/core/domain.py",
  "$Package/core/tex.py",
  "$Package/core/questions.py",
  "$Package/core/question.py",
  "$Package/core/serialize.py",
  "$Package/core/paper.py",
  "$Package/core/store.py",
  "$Package/core/sources.py",
  "$Package/core/registry.py",
  "$Package/core/release.py",
  "$Package/core/composition.py",
  "$Package/core/render_model.py",
  "$Package/core/figure_render.py"
)) { Require-File $File }

# --- service layer ----------------------------------------------------------
foreach ($File in @(
  "$Package/service/__init__.py",
  "$Package/service/context.py",
  "$Package/service/library.py",
  "$Package/service/extraction.py",
  "$Package/service/composition.py",
  "$Package/service/capture.py",
  "$Package/service/events.py",
  "$Package/service/tex_builder.py",
  "$Package/service/tex_quality.py",
  "$Package/service/rendering/__init__.py",
  "$Package/service/rendering/errors.py",
  "$Package/service/rendering/paths.py",
  "$Package/service/rendering/text.py",
  "$Package/service/rendering/inline_tex.py",
  "$Package/service/rendering/validation.py",
  "$Package/service/rendering/catalogs.py",
  "$Package/service/rendering/content.py",
  "$Package/service/rendering/document.py",
  "$Package/service/facade.py"
)) { Require-File $File }

# --- adapters and entrypoints ----------------------------------------------
foreach ($File in @(
  "$Package/mcp/__init__.py",
  "$Package/mcp/server.py",
  "$Package/api/__init__.py",
  "$Package/api/main.py",
  "$Package/api/factory.py",
  "$Package/api/routes.py",
  "$Package/api/dependencies.py",
  "$Package/api/logging.py",
  "$Package/launcher/__init__.py",
  "$Package/launcher/main.py",
  "$Package/launcher/supervisor.py",
  "$Package/launcher/static_server.py",
  "$Package/tex/npee-math-exam.cls",
  "$Package/tex/CLASS-API.md",
  "$Package/frontend/package.json",
  "$Package/frontend/src/main.tsx",
  "collections/README.md",
  "AGENTS.md",
  "README.md"
)) { Require-File $File }

foreach ($Directory in @($Package, "$Package/core", "$Package/service", "$Package/mcp", "$Package/api", "$Package/launcher", "$Package/tex", "$Package/frontend", "docs", "collections")) {
  Require-Directory $Directory
}

# --- directories that must not exist ---------------------------------------
foreach ($Retired in @(
  "$Package/cli",
  "app/backend",
  "app/frontend",
  "app/data_service",
  "app/data/papers",
  "app/data/catalogs.json",
  "agent",
  "library",
  "imports",
  "scripts"
)) {
  if (Test-Path -LiteralPath (Resolve-Repo $Retired)) {
    throw "Retired path still exists: $Retired"
  }
}

# --- the class stays source-agnostic ---------------------------------------
$ClassText = [System.IO.File]::ReadAllText((Resolve-Repo "$Package/tex/npee-math-exam.cls"))
foreach ($Pattern in @(
  '\\NeedsTeXFormat\{LaTeX2e\}',
  '\\ProvidesClass\{npee-math-exam\}',
  '\\newcommand\{\\NPEESetup\}',
  '\\newenvironment\{ExamChoiceQuestion\}',
  '\\newenvironment\{ExamFillQuestion\}',
  '\\NewDocumentEnvironment\{ExamSolution\}'
)) {
  if ($ClassText -notmatch $Pattern) { throw "Class API pattern is missing: $Pattern" }
}
if ($ClassText -match '(?i)(npee-math-papers|zhangyu|liyanfang|yubingsen|lilin|chaoyue|euclid)') {
  throw 'The generic class must not reference a data root or publication name.'
}
if ($ClassText -notmatch '\\protected\\def\\sum\{\\mathop\{\\displaystyle\\NPEEOriginalSum\}\\limits\}') {
  throw 'The generic class must force sum limits above and below the operator.'
}
if ($ClassText -notmatch '(?m)\\DeclareOption\{a3\}' -or $ClassText -notmatch '(?i)paperwidth=420mm,paperheight=297mm') {
  throw 'Landscape A3 layout support is missing from the active class.'
}

# --- the store is the only file layer --------------------------------------
$StoreText = [System.IO.File]::ReadAllText((Resolve-Repo "$Package/core/store.py"))
if ($StoreText -notmatch 'def write_paper' -or $StoreText -notmatch 'atomic') {
  throw 'The store must expose atomic writes.'
}

# --- adapters must share the service facade --------------------------------
$McpText = [System.IO.File]::ReadAllText((Resolve-Repo "$Package/mcp/server.py"))
if ($McpText -notmatch 'NpeeService' -or $McpText -notmatch 'FastMCP') {
  throw 'The MCP server must be a FastMCP adapter over NpeeService.'
}
$RoutesText = [System.IO.File]::ReadAllText((Resolve-Repo "$Package/api/routes.py"))
if ($RoutesText -notmatch 'NpeeService') {
  throw 'The HTTP API must be an adapter over NpeeService.'
}

# --- the data root name is fixed -------------------------------------------
$RootText = [System.IO.File]::ReadAllText((Resolve-Repo "$Package/core/store.py"))
if ($RootText -notmatch '\.npee-math-papers') {
  throw 'The store must resolve the .npee-math-papers data root.'
}

Write-Output 'Passed architecture audit: core, service, HTTP, MCP and launcher boundaries are valid.'
