import type { ReactNode } from "react";

import { classNames } from "./classNames";

export type MetricTone = "green" | "blue" | "amber" | "red";

export function MetricCard({
  icon,
  label,
  value,
  detail,
  tone = "green",
  loading = false,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: MetricTone;
  loading?: boolean;
}) {
  return (
    <div className={classNames("metric-card", loading && "is-loading")}>
      <span className={classNames("metric-icon", `metric-${tone}`)}>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        {detail !== undefined && detail !== null && detail !== "" ? <span>{detail}</span> : null}
      </div>
    </div>
  );
}
