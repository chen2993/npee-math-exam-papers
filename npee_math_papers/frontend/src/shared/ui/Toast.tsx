/**
 * Toast notifications.
 *
 * A tiny context-backed queue. Pages call `useToast().notify("…")` instead of
 * threading a setter down through props, which is what let the old AppShell own
 * unrelated view state. Success and error toasts share one renderer and one
 * auto-dismiss rule.
 */

import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { classNames } from "./classNames";
import { IconButton } from "./Button";

export type ToastTone = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
  /** Milliseconds before auto-dismiss; 0 keeps it until dismissed. */
  durationMs: number;
}

interface ToastContextValue {
  notify: (message: string, tone?: ToastTone, durationMs?: number) => void;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);
let nextId = 1;

const TONE_ICON = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
} as const;

export function ToastProvider({ children, defaultDurationMs = 2600 }: { children: ReactNode; defaultDurationMs?: number }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, tone: ToastTone = "success", durationMs = defaultDurationMs) => {
      const text = message.trim();
      if (!text) return;
      setItems((current) => [...current.slice(-3), { id: nextId++, message: text, tone, durationMs }]);
    },
    [defaultDurationMs],
  );

  const value = useMemo(() => ({ notify, dismiss }), [notify, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {items.map((item) => (
          <ToastCard key={item.id} item={item} onDismiss={() => dismiss(item.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastCard({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const Icon = TONE_ICON[item.tone];
  useEffect(() => {
    if (!item.durationMs) return undefined;
    const timer = window.setTimeout(onDismiss, item.durationMs);
    return () => window.clearTimeout(timer);
  }, [item.durationMs, onDismiss]);

  return (
    <div className={classNames("toast", `toast-${item.tone}`)}>
      <Icon size={16} />
      <span>{item.message}</span>
      <IconButton label="关闭" size="sm" onClick={onDismiss}>
        <X size={13} />
      </IconButton>
    </div>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast 必须在 ToastProvider 内使用");
  return context;
}
