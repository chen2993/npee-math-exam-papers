import type { CompositionDraft } from "../../domain/composition/models";
import type { CompositionDraftRepository } from "../../application/composition/ports";

const STORAGE_KEY = "npee-library-compositions-v4";

interface StoredWorkspace {
  schema_version: number;
  drafts: CompositionDraft[];
}

/**
 * 用 localStorage 持久化组卷草稿，并带显式 schema 版本。
 *
 * 把数组包在带版本的对象里，未来格式变化可被识别并迁移，而不是被误读。无法解析的
 * 数据直接丢弃，避免单条损坏阻塞整个工作区。
 */
export class BrowserCompositionDraftRepository implements CompositionDraftRepository {
  constructor(private readonly storageKey = STORAGE_KEY) {}

  load(): CompositionDraft[] {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        // v3 形态：裸数组。
        return parsed as CompositionDraft[];
      }
      if (parsed && typeof parsed === "object" && Array.isArray((parsed as StoredWorkspace).drafts)) {
        return (parsed as StoredWorkspace).drafts;
      }
      return [];
    } catch {
      localStorage.removeItem(this.storageKey);
      return [];
    }
  }

  save(drafts: CompositionDraft[]): void {
    const payload: StoredWorkspace = { schema_version: 1, drafts };
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(payload));
    } catch {
      // 存储可能已满或被禁用；草稿在本次会话内仍保留在内存中。
    }
  }
}
