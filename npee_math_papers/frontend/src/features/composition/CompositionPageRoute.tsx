/**
 * 组卷工作台。
 *
 * 组卷内容**全部来自用户**：导入一份导出的 JSON，或打开 `composition/` 下的正式
 * 组卷包（打开＝读成新草稿，保存＝写回原包）。因此没有默认草稿，也没有空转的
 * 按钮——每个控件在当前状态下都有明确效果。
 *
 * 布局：草稿标签行 → 当前组卷摘要与动作 → 仓库组卷包 → 编译进度 → 已选套卷 /
 * 文档设置 → 选卷区。
 */

import {
  ArrowDown,
  ArrowUp,
  Copy,
  FileDown,
  FileJson,
  FileUp,
  GripVertical,
  ListPlus,
  Plus,
  Save,
  Settings2,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import type { PaperOrder } from "../../application/catalog/ports";
import type { CompositionPackageSummary } from "../../application/composition/ports";
import { useOverview, usePapers } from "../../application/query/hooks";
import { useAppServices } from "../../app/AppServices";
import { useCompile, useWorkspace } from "../../app/CompositionWorkspace";
import {
  buildCompilePayload,
  draftFromCompositionDocument,
  draftFromCompilePayload,
  outputTargetCount,
  type CompositionDraft,
  type Layout,
  type Spacing,
  type Theme,
} from "../../domain/composition/models";
import { subjectNames, type PaperSummary, type Subject } from "../../domain/catalog/models";
import { usePreferences } from "../../preferences";
import { useDragReorder } from "../../shared/hooks/useDragReorder";
import {
  Button,
  CheckField,
  ConfirmDialog,
  EmptyState,
  IconButton,
  Pager,
  SelectField,
  Surface,
  SurfaceHeading,
  TextAreaField,
  TextField,
  classNames,
  useToast,
} from "../../shared/ui";
import { EMPTY_PAPER_FILTERS, PaperFilters, type PaperFilterValue } from "../catalog/PaperFilters";
import { CompilePanel } from "./CompilePanel";

export default function CompositionPageRoute() {
  const { gateway, exportGateway } = useAppServices();
  const { preferences } = usePreferences();
  const workspace = useWorkspace();
  const toast = useToast();
  // The compile job is app-wide state (see CompositionWorkspace): a typeset run
  // outlives the page, so leaving and returning must not lose the progress or the
  // finished artifacts. It is a separate context so polling does not re-render
  // every page that reads a draft.
  const compileFlow = useCompile();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [pickerOffset, setPickerOffset] = useState(0);
  const [pickerFilters, setPickerFilters] = useState<PaperFilterValue>(EMPTY_PAPER_FILTERS);
  const [pickerOrder, setPickerOrder] = useState<PaperOrder>("series");
  /** 当前草稿来自哪个组卷包（空表示它只存在于浏览器草稿里）。 */
  const [openedPackage, setOpenedPackage] = useState<{ packageId: string; draftId: string } | null>(null);
  const importInput = useRef<HTMLInputElement>(null);

  // 组卷包是仓库里的真实文件；列表很小，随页面加载一次即可。
  const packages = useQuery({
    queryKey: ["npee", "composition-packages"],
    queryFn: ({ signal }) => exportGateway.packages(signal),
  });

  const overview = useOverview(gateway);
  const papers = usePapers(gateway, {
    seriesKeys: pickerFilters.seriesKey ? [pickerFilters.seriesKey] : [],
    years: pickerFilters.year ? [Number(pickerFilters.year)] : [],
    subjects: pickerFilters.subject ? [pickerFilters.subject] : [],
    query: pickerFilters.query,
    order: pickerOrder,
    offset: pickerOffset,
    limit: preferences.pageSize,
  });
  // The server filters, orders and pages; the picker renders its page verbatim.
  const rows = papers.data?.papers ?? [];

  const years = useMemo(
    () => [...(overview.data?.stats.years ?? [])].sort((left, right) => right - left),
    [overview.data?.stats.years],
  );

  /** Any filter change invalidates the current offset, so paging restarts. */
  function changePickerFilters(patch: Partial<PaperFilterValue>) {
    setPickerFilters((current) => ({ ...current, ...patch }));
    setPickerOffset(0);
  }

  function changePickerOrder(next: PaperOrder) {
    setPickerOrder(next);
    setPickerOffset(0);
  }

  const draft = workspace.activeDraft;
  const selectedCount = draft?.papers.length ?? 0;
  const selectedKeys = useMemo(() => new Set((draft?.papers ?? []).map((paper) => paper.natural_key)), [draft?.papers]);
  const drag = useDragReorder(workspace.reorderPapers);
  // 题数只在全部引用都已知时才算得准；导入的引用先只有自然键，回填完成前
  // 不要显示一个假的「0 题」。
  const totalQuestions = useMemo(() => {
    const refs = draft?.papers ?? [];
    if (!refs.length || refs.some((paper) => !paper.question_count)) return null;
    return refs.reduce((sum, paper) => sum + paper.question_count, 0);
  }, [draft?.papers]);
  // Each layout × theme × spacing combination is its own PDF, so "both" on all
  // three silently means eight files. Surface it before the run starts.
  const targetCount = useMemo(() => (draft ? outputTargetCount(draft) : 0), [draft]);

  // 组卷引用只带自然键；题数与系列名要从套卷目录回填。导入 JSON 或打开组卷包时
  // 这些字段是空的，不回填的话界面上会一直显示「0 题」。
  useEffect(() => {
    if (!draft || !rows.length) return;
    const byKey = new Map(rows.map((paper) => [paper.natural_key, paper]));
    const stale = draft.papers.filter((ref) => {
      const found = byKey.get(ref.natural_key);
      return found && (ref.question_count !== found.question_count || ref.series_name !== found.series_name);
    });
    if (!stale.length) return;
    workspace.updateActiveDraft((current) => ({
      ...current,
      papers: current.papers.map((ref) => {
        const found = byKey.get(ref.natural_key);
        return found ? { ...ref, question_count: found.question_count, series_name: found.series_name } : ref;
      }),
    }));
  }, [draft, rows, workspace]);


  function exportJson() {
    if (!draft) return;
    const payload = buildCompilePayload(draft);
    downloadBlob(new Blob([JSON.stringify(payload, null, 2) + "\n"], { type: "application/json" }), `${draft.id}.json`);
    toast.notify("组卷 JSON 已导出");
  }

  /**
   * Import a previously exported composition JSON as a new draft.
   *
   * Export was a dead end before this: the file could be downloaded but never
   * read back. Import always appends a draft (never overwrites), so a round trip
   * is non-destructive and the imported copy can be compared side by side.
   */
  async function importJson(file: File) {
    try {
      const imported = draftFromCompilePayload(JSON.parse(await file.text()));
      const created = workspace.importDraft(imported);
      toast.notify(`已导入「${created.name}」，共 ${created.papers.length} 套`);
    } catch (reason) {
      toast.notify(reason instanceof Error ? reason.message : "导入失败：无法解析该文件", "error");
    }
  }

  /** 打开仓库里的组卷包：把它读成草稿并作为新草稿加入，原包不被动过。 */
  async function openPackage(compositionId: string) {
    try {
      const document = await exportGateway.openPackage(compositionId);
      const imported = draftFromCompositionDocument(document.composition, compositionId);
      const created = workspace.importDraft(imported);
      // 写回权限绑定在这份草稿上：复制出的副本 id 不同，自然不会覆盖原包。
      setOpenedPackage({ packageId: compositionId, draftId: created.id });
      toast.notify(`已打开「${created.name}」，共 ${created.papers.length} 套`);
    } catch (reason) {
      toast.notify(reason instanceof Error ? reason.message : "打开组卷包失败", "error");
    }
  }

  /**
   * 把当前草稿写回它所属的组卷包。
   *
   * 只有"从某个包打开过"的草稿才允许写回，而且判据取的是**当前草稿 id**：
   * 复制出来的草稿有新的 id，因此不会误覆盖原包。
   */
  async function saveToPackage() {
    if (!draft || !openedPackage || draft.id !== openedPackage.draftId) return;
    try {
      const payload = buildCompilePayload(draft);
      await exportGateway.savePackage(openedPackage.packageId, payload);
      await packages.refetch();
      toast.notify("已保存回组卷包");
    } catch (reason) {
      toast.notify(reason instanceof Error ? reason.message : "保存组卷包失败", "error");
    }
  }

  async function compile() {
    if (!draft || compileFlow.isBusy || !selectedCount) return;
    await compileFlow.start(buildCompilePayload(draft), draft.id);
  }

  async function downloadArtifact(index: number) {
    try {
      const result = await compileFlow.download(undefined, index);
      if (result) {
        downloadBlob(result.blob, result.filename);
        toast.notify(result.format === "zip" ? "多目标 PDF 已打包导出" : "PDF 已下载");
      }
    } catch (reason) {
      toast.notify(reason instanceof Error ? reason.message : "下载失败", "error");
    }
  }

  /** 隐藏的文件选择框：导入入口在页头和空状态里各有一处，共用这一个。 */
  function renderImportInput() {
    return (
      <input
        ref={importInput}
        type="file"
        accept="application/json,.json"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          // 先清空，这样连续选同一个文件也会再次触发 change。
          event.target.value = "";
          if (file) void importJson(file);
        }}
      />
    );
  }

  // 没有草稿时只显示"导入/打开"的入口：组卷内容全部来自用户，
  // 界面上不预置任何默认草稿。
  if (!draft) {
    return (
      <div className="page-stack">
        <div className="page-title-row">
          <div>
            <span className="eyebrow">NPEE COMPOSITIONS</span>
            <h2>组卷</h2>
            <p>导入组卷 JSON，或直接打开仓库里的组卷包，然后编译导出 PDF。</p>
          </div>
        </div>

        <Surface className="compose-blank">
          <EmptyState
            icon={<FileJson size={25} />}
            title="还没有组卷"
            hint="导入一份组卷 JSON，或从下面的仓库组卷包里挑一个打开"
            action={
              <Button variant="primary" icon={<FileUp size={16} />} onClick={() => importInput.current?.click()}>
                导入组卷 JSON
              </Button>
            }
          />
        </Surface>

        <PackageStrip
          packages={packages.data ?? []}
          loading={packages.isLoading}
          error={packages.isError ? packages.error : null}
          openedPackageId={openedPackage?.packageId ?? null}
          onOpen={(compositionId) => void openPackage(compositionId)}
          onSave={null}
          onNewDraft={() => {
            workspace.addDraft();
            toast.notify("已新建空组卷");
          }}
        />

        {renderImportInput()}
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="draft-toolbar surface">
        <div className="draft-toolbar-heading">
          <span className="eyebrow">NPEE COMPOSITIONS</span>
          <strong>
            我的组卷 <small>{workspace.drafts.length} 个草稿</small>
          </strong>
        </div>
        <div className="draft-tabs" role="tablist">
          {workspace.drafts.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={item.id === workspace.activeDraftId}
              className={classNames("draft-tab", item.id === workspace.activeDraftId && "is-active")}
              onClick={() => workspace.setActiveDraftId(item.id)}
            >
              {item.name || "未命名组卷"}
              <span>{item.papers.length}</span>
            </button>
          ))}
          <IconButton label="新建空组卷" className="draft-add" onClick={() => workspace.addDraft()}>
            <Plus size={16} />
          </IconButton>
        </div>
        <div className="draft-toolbar-actions">
          <IconButton
            label="复制当前组卷"
            onClick={() => {
              workspace.duplicateActiveDraft();
              toast.notify("已复制当前组卷");
            }}
          >
            <Copy size={16} />
          </IconButton>
          <IconButton label="删除当前组卷" tone="danger" onClick={() => setConfirmDelete(true)}>
            <Trash2 size={16} />
          </IconButton>
        </div>
      </div>

      <div className="page-title-row">
        <div>
          <span className="eyebrow">CURRENT COMPOSITION</span>
          <h2>{draft.name || "未命名组卷"}</h2>
          <p>
            已选 {selectedCount} 套{totalQuestions === null ? "" : ` · 共 ${totalQuestions} 题`} · 本次将生成{" "}
            {targetCount} 份 PDF
            {openedPackage?.draftId === draft.id ? ` · 已打开组卷包 ${openedPackage.packageId}` : ""}
          </p>
        </div>
        <div className="page-title-actions">
          <Button
            variant="primary"
            icon={<FileDown size={16} />}
            onClick={() => void compile()}
            disabled={!selectedCount || compileFlow.isBusy}
          >
            {compileFlow.isBusy ? "编译进行中…" : "编译导出"}
          </Button>
          <Button
            icon={<FileUp size={16} />}
            onClick={() => importInput.current?.click()}
          >
            导入
          </Button>
          <Button
            icon={<FileJson size={16} />}
            onClick={exportJson}
            disabled={!selectedCount}
          >
            导出
          </Button>
        </div>
      </div>

      <PackageStrip
        packages={packages.data ?? []}
        loading={packages.isLoading}
        error={packages.isError ? packages.error : null}
        openedPackageId={openedPackage?.packageId ?? null}
        onOpen={(compositionId) => void openPackage(compositionId)}
        onSave={openedPackage?.draftId === draft.id ? () => void saveToPackage() : null}
        saveLabel={openedPackage?.packageId ?? ""}
      />

      {renderImportInput()}


      <CompilePanel
        phase={compileFlow.phase}
        job={compileFlow.job}
        error={compileFlow.error}
        elapsedSeconds={compileFlow.elapsedSeconds}
        onDownload={(index) => void downloadArtifact(index)}
        onDismiss={compileFlow.reset}
      />

      <div className="compose-layout">
        <Surface className="compose-selected">
          <SurfaceHeading
            eyebrow="CURRENT SELECTION"
            title="已选套卷"
            count={selectedCount}
            actions={
              <Button size="sm" variant="quiet" onClick={() => setConfirmClear(true)} disabled={!selectedCount}>
                清空
              </Button>
            }
          />
          {selectedCount > 1 ? (
            <p className="selected-hint">拖动行可调整打印顺序，也可用上移/下移按钮。</p>
          ) : null}
          {selectedCount ? (
            <div className="selected-list">
              {draft.papers.map((paper, index) => (
                <div
                  className={classNames(
                    "selected-paper",
                    drag.draggingIndex === index && "is-dragging",
                    drag.dropIndex === index && drag.draggingIndex !== null && "is-drop-target",
                  )}
                  key={paper.natural_key}
                  draggable
                  onDragStart={() => drag.onDragStart(index)}
                  onDragOver={(event) => {
                    // Required, or the drop event never fires.
                    event.preventDefault();
                    drag.onDragOver(index);
                  }}
                  onDragEnd={drag.onDragEnd}
                  onDrop={(event) => {
                    event.preventDefault();
                    drag.onDrop(index);
                  }}
                >
                  <span className="selected-grip" aria-hidden="true">
                    <GripVertical size={14} />
                  </span>
                  <span className="selected-index">{String(index + 1).padStart(2, "0")}</span>
                  <div className="selected-paper-text">
                    <strong>
                      {paper.series_name} · 第{paper.paper_no}套
                    </strong>
                    <small>
                      {paper.year} · {subjectNames[paper.subject as Subject] ?? paper.subject}
                      {paper.question_count ? ` · ${paper.question_count} 题` : ""}
                    </small>
                  </div>
                  <div className="selected-actions">
                    <IconButton label="上移" size="sm" disabled={index === 0} onClick={() => workspace.movePaper(index, -1)}>
                      <ArrowUp size={15} />
                    </IconButton>
                    <IconButton
                      label="下移"
                      size="sm"
                      disabled={index === selectedCount - 1}
                      onClick={() => workspace.movePaper(index, 1)}
                    >
                      <ArrowDown size={15} />
                    </IconButton>
                    <IconButton label="移除" size="sm" tone="danger" onClick={() => workspace.removePaper(paper.natural_key)}>
                      <X size={15} />
                    </IconButton>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon={<FileJson size={25} />} title="还没有选择套卷" hint="从下方目录加入试卷，开始构建组合" />
          )}
        </Surface>

        <DocumentSettings draft={draft} onUpdate={workspace.updateActiveDraft} />
      </div>

      <Surface className="compose-pool">
        <SurfaceHeading
          eyebrow="PAPER PICKER"
          title="选择套卷"
          count={`${papers.data?.total ?? 0} 套`}
          actions={
            <Button
              size="sm"
              icon={<ListPlus size={14} />}
              disabled={!rows.length || rows.every((paper) => selectedKeys.has(paper.natural_key))}
              onClick={() => {
                const added = workspace.addPapers(rows);
                toast.notify(added ? `已加入本页 ${added} 套` : "本页套卷都已在组卷中");
              }}
            >
              加入本页全部
            </Button>
          }
        />
        <div className="compose-pool-filters">
          <PaperFilters
            value={pickerFilters}
            series={overview.data?.series ?? []}
            years={years}
            onChange={changePickerFilters}
            order={pickerOrder}
            onOrderChange={changePickerOrder}
            trailing={
              <span className="tool-count">
                {papers.isFetching ? "读取中…" : `${papers.data?.total ?? 0} 套`}
              </span>
            }
          />
        </div>
        <div className="paper-table-scroll">
          <table className="paper-table-plain">
            <thead>
              <tr>
                <th className="paper-table-check" aria-label="选择">
                  <input
                    type="checkbox"
                    aria-label="选择本页全部"
                    checked={Boolean(rows.length) && rows.every((paper) => selectedKeys.has(paper.natural_key))}
                    ref={(node) => {
                      // A partially-selected page reads as "indeterminate": a plain
                      // checkbox would otherwise claim nothing is selected.
                      if (node) {
                        const some = rows.some((paper) => selectedKeys.has(paper.natural_key));
                        node.indeterminate = some && !node.checked;
                      }
                    }}
                    disabled={!rows.length}
                    onChange={() => {
                      const all = rows.every((paper) => selectedKeys.has(paper.natural_key));
                      if (all) {
                        const added = workspace.removePapers(rows.map((paper) => paper.natural_key));
                        toast.notify(added ? `已移除本页 ${added} 套` : "本页套卷都不在组卷中");
                      } else {
                        const added = workspace.addPapers(rows);
                        toast.notify(added ? `已加入本页 ${added} 套` : "本页套卷都已在组卷中");
                      }
                    }}
                  />
                </th>
                <th>套卷</th>
                <th>年份</th>
                <th>科目</th>
                <th>题目</th>
                <th>选择</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((paper) => (
                <PickerRow
                  key={paper.natural_key}
                  paper={paper}
                  selected={selectedKeys.has(paper.natural_key)}
                  onToggle={workspace.togglePaper}
                />
              ))}
            </tbody>
          </table>
          {!rows.length && !papers.isLoading ? (
            <EmptyState
              title={pickerFilters.query ? "没有匹配的套卷" : "没有可选的套卷"}
              hint={pickerFilters.query ? "换一个关键词，或清除筛选条件" : "请先导入题目"}
            />
          ) : null}
        </div>
        <Pager
          offset={pickerOffset}
          count={papers.data?.papers.length ?? 0}
          total={papers.data?.total ?? 0}
          pageSize={preferences.pageSize}
          onChange={setPickerOffset}
          disabled={papers.isFetching}
        />
      </Surface>

      <ConfirmDialog
        open={confirmDelete}
        title="删除当前组卷？"
        message={`将删除「${draft.name || "未命名组卷"}」及其 ${selectedCount} 套选择，此操作无法撤销。`}
        confirmLabel="删除"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          setConfirmDelete(false);
          const removed = workspace.deleteActiveDraft();
          toast.notify(removed ? "已删除组卷" : "没有可删除的组卷", removed ? "success" : "error");
        }}
      />

      <ConfirmDialog
        open={confirmClear}
        title="清空已选套卷？"
        message={`将移除当前组卷的 ${selectedCount} 套选择，组卷本身保留。`}
        confirmLabel="清空"
        onCancel={() => setConfirmClear(false)}
        onConfirm={() => {
          setConfirmClear(false);
          workspace.clearPapers();
          toast.notify("已清空选择");
        }}
      />
    </div>
  );
}

/**
 * One row of the paper picker.
 *
 * 整行可点，末尾另有一个真实的「加入 / 移除」按钮。早先那是一个纯装饰的胶囊标签，
 * 看起来像按钮却不响应——读者点了没反应，只能去猜要先勾复选框。
 */
function PickerRow({
  paper,
  selected,
  onToggle,
}: {
  paper: PaperSummary;
  selected: boolean;
  onToggle: (paper: PaperSummary) => void;
}) {
  return (
    <tr
      className={classNames("picker-row", selected && "is-selected")}
      onClick={() => onToggle(paper)}
      title={selected ? "点击移除" : "点击加入组卷"}
    >
      <td className="paper-table-check">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggle(paper)}
          onClick={(event) => event.stopPropagation()}
          aria-label={`${selected ? "移除" : "加入"} ${paper.natural_key}`}
        />
      </td>
      <td>
        <div className="paper-table-title">
          <span className={classNames("subject-mark", paper.subject)}>{paper.subject.replace("math", "数")}</span>
          <span>
            <strong>
              {paper.series_name} 第 {paper.paper_no} 套
            </strong>
            <small>{paper.natural_key}</small>
          </span>
        </div>
      </td>
      <td data-label="年份">{paper.year}</td>
      <td data-label="科目">{subjectNames[paper.subject]}</td>
      <td data-label="题目">{paper.question_count}</td>
      <td>
        <Button
          size="sm"
          variant={selected ? "primary" : "default"}
          onClick={(event) => {
            // 整行也是开关，这里必须吞掉冒泡，否则会切换两次。
            event.stopPropagation();
            onToggle(paper);
          }}
        >
          {selected ? "移除" : "加入"}
        </Button>
      </td>
    </tr>
  );
}

/**
 * 仓库里的正式组卷包（``composition/<id>/``）。
 *
 * 两个动作分工明确：**打开**把包读成一份新草稿（原文件不动），**保存**才写回原包。
 * 保存按钮只在当前草稿确实来自某个包时渲染，所以界面里不会出现永久禁用的按钮。
 */
function PackageStrip({
  packages,
  loading,
  error,
  openedPackageId,
  onOpen,
  onSave,
  saveLabel,
  onNewDraft,
}: {
  packages: CompositionPackageSummary[];
  loading: boolean;
  error: unknown;
  openedPackageId: string | null;
  onOpen: (compositionId: string) => void;
  /** 为空表示当前草稿不对应任何包，此时不显示保存入口。 */
  onSave: (() => void) | null;
  saveLabel?: string;
  onNewDraft?: () => void;
}) {
  return (
    <div className="package-strip">
      <span className="package-strip-label">仓库组卷包</span>

      {loading ? <span className="package-strip-hint">读取中…</span> : null}
      {error ? (
        <span className="package-strip-hint">
          {error instanceof Error ? error.message : "读取失败"}
        </span>
      ) : null}

      {packages.map((item) => (
        <button
          key={item.composition_id}
          type="button"
          className={classNames("package-chip", openedPackageId === item.composition_id && "is-open")}
          title={`${item.composition_id} · ${item.paper_count} 套 · ${item.target_count} 个产物`}
          onClick={() => onOpen(item.composition_id)}
        >
          <strong>{item.title}</strong>
          <small>
            {item.paper_count} 套 · {item.target_count} 份
          </small>
        </button>
      ))}

      {!loading && !error && !packages.length ? (
        <span className="package-strip-hint">composition/ 下还没有组卷包</span>
      ) : null}

      {onSave ? (
        <Button size="sm" variant="quiet" icon={<Save size={14} />} onClick={onSave}>
          保存回 {saveLabel}
        </Button>
      ) : null}

      {onNewDraft ? (
        <Button size="sm" variant="quiet" icon={<Plus size={14} />} onClick={onNewDraft}>
          新建空组卷
        </Button>
      ) : null}
    </div>
  );
}

function DocumentSettings({
  draft,
  onUpdate,
}: {
  draft: CompositionDraft;
  onUpdate: (update: (draft: CompositionDraft) => CompositionDraft) => void;
}) {
  return (
    <Surface className="compose-settings">
      <SurfaceHeading eyebrow="DOCUMENT SETTINGS" title="文档信息" actions={<Settings2 size={17} className="muted-icon" />} />

      <TextField
        label="显示名称"
        value={draft.name}
        onChange={(event) => onUpdate((current) => ({ ...current, name: event.target.value }))}
      />

      <div className="setting-columns">
        <SelectField
          label="页面"
          value={draft.layout}
          onChange={(event) =>
            onUpdate((current) => ({ ...current, layout: event.target.value as Layout }))
          }
        >
          <option value="both">A3 + A4</option>
          <option value="a3">A3</option>
          <option value="a4">A4</option>
        </SelectField>
        <SelectField
          label="纸色"
          value={draft.theme}
          onChange={(event) => onUpdate((current) => ({ ...current, theme: event.target.value as Theme }))}
        >
          <option value="print">白纸</option>
          <option value="cream">考试米黄</option>
          <option value="both">两种纸色</option>
        </SelectField>
      </div>

      <div className="setting-columns">
        <SelectField
          label="间距（大题）"
          value={draft.spacing}
          onChange={(event) => onUpdate((current) => ({ ...current, spacing: event.target.value as Spacing }))}
          hint="只影响解答题：紧凑为自然连排，宽松让每题独占页面以便书写。"
        >
          <option value="compact">紧凑（连排）</option>
          <option value="spaced">宽松（每题一页）</option>
          <option value="both">两种间距</option>
        </SelectField>
        <SelectField
          label="留白（打印）"
          value={draft.printBlank ? "on" : "off"}
          onChange={(event) => onUpdate((current) => ({ ...current, printBlank: event.target.value === "on" }))}
          hint="与间距无关：每套卷补足整页、封面后加空白页、目录凑成偶数页。"
        >
          <option value="on">留白（打印交付）</option>
          <option value="off">不留白（紧凑）</option>
        </SelectField>
      </div>

      <CheckField label="生成目录" checked={draft.toc} onChange={(checked) => onUpdate((current) => ({ ...current, toc: checked }))} />

      <div className="setting-divider" />
      <div className="setting-subheading">试卷封面页</div>
      <CheckField
        label="显示封面页"
        checked={draft.opening.show}
        onChange={(checked) => onUpdate((current) => ({ ...current, opening: { ...current.opening, show: checked } }))}
      />
      <CheckField
        label="考生信息"
        checked={draft.opening.candidateInfo}
        disabled={!draft.opening.show}
        onChange={(checked) => onUpdate((current) => ({ ...current, opening: { ...current.opening, candidateInfo: checked } }))}
      />
      <CheckField
        label="注意事项"
        checked={draft.opening.notices}
        disabled={!draft.opening.show}
        onChange={(checked) => onUpdate((current) => ({ ...current, opening: { ...current.opening, notices: checked } }))}
      />

      <div className="setting-divider" />
      <div className="setting-subheading">页面水印</div>
      <CheckField
        label="启用水印"
        checked={draft.watermark.enabled}
        onChange={(checked) => onUpdate((current) => ({ ...current, watermark: { ...current.watermark, enabled: checked } }))}
      />
      <TextAreaField
        label="水印文本"
        rows={2}
        value={draft.watermark.text}
        disabled={!draft.watermark.enabled}
        placeholder="例如：内部资料"
        onChange={(event) => onUpdate((current) => ({ ...current, watermark: { ...current.watermark, text: event.target.value } }))}
      />
      <TextField
        label="整体透明度"
        type="number"
        min={0}
        max={1}
        step={0.01}
        value={draft.watermark.opacity}
        disabled={!draft.watermark.enabled}
        onChange={(event) =>
          onUpdate((current) => ({
            ...current,
            watermark: { ...current.watermark, opacity: Math.min(1, Math.max(0, Number(event.target.value) || 0)) },
          }))
        }
      />

      <div className="setting-note">
        <Sparkles size={15} />
        <span>编译经应用 API 完成，组卷引用会按当前题库内容自动绑定版本。</span>
      </div>
    </Surface>
  );
}

/** Trigger a browser download for a blob. */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
