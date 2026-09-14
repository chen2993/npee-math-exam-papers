/**
 * Confirmation dialog for destructive actions.
 *
 * Deleting a draft or clearing a selection is one mis-click away from losing
 * work, so those actions ask first. The dialog is a native ``<dialog>``-style
 * overlay with focus handled on mount and Escape to cancel.
 */

import { AlertTriangle } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

import { Button } from "./Button";

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "确认",
  cancelLabel = "取消",
  tone = "danger",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    confirmRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="dialog-backdrop" onClick={onCancel} role="presentation">
      <div className="dialog" role="alertdialog" aria-modal="true" aria-label={title} onClick={(event) => event.stopPropagation()}>
        <span className="dialog-icon">
          <AlertTriangle size={19} />
        </span>
        <h3>{title}</h3>
        <p>{message}</p>
        <div className="dialog-actions">
          <Button onClick={onCancel}>{cancelLabel}</Button>
          <Button ref={confirmRef} variant={tone === "danger" ? "danger" : "primary"} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
