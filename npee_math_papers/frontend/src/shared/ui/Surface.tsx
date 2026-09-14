/**
 * Surface, panel heading and empty-state primitives.
 *
 * `Surface` is the one card/panel shell (border + radius + shadow from tokens),
 * `SurfaceHeading` is its standard header, and `EmptyState` normalises the
 * "nothing here yet" block that every table would otherwise hand-roll.
 */

import type { ReactNode } from "react";

import { classNames } from "./classNames";

export function Surface({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={classNames("surface", className)}>{children}</section>;
}

export function SurfaceHeading({
  eyebrow,
  title,
  count,
  actions,
  className,
}: {
  eyebrow?: string;
  title: ReactNode;
  count?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header className={classNames("surface-heading", className)}>
      <div className="surface-heading-text">
        {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
        <h3>
          {title}
          {count !== undefined && count !== null ? <span className="inline-count">{count}</span> : null}
        </h3>
      </div>
      {actions ? <div className="surface-heading-actions">{actions}</div> : null}
    </header>
  );
}

export function EmptyState({
  icon,
  title,
  hint,
  action,
  className,
}: {
  icon?: ReactNode;
  title: ReactNode;
  hint?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={classNames("empty-state", className)}>
      {icon}
      <strong>{title}</strong>
      {hint ? <span>{hint}</span> : null}
      {action}
    </div>
  );
}
