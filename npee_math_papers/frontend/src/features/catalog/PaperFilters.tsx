/**
 * The paper filter bar, shared by the catalogue and the composition picker.
 *
 * Both screens need "narrow the library by year / subject / series, then search
 * within the result". Keeping one control means the two never drift apart, and a
 * new filter is added once. Filter state is a plain object so the catalogue can
 * keep it in the URL and the picker can keep it in component state.
 *
 * Every field is labelled. The unlabelled selects looked tidy but forced the
 * user to read the option text to know which axis they were on, which is a real
 * cost once the three dropdowns all read "全部…".
 */

import { X } from "lucide-react";

import type { PaperOrder } from "../../application/catalog/ports";
import type { Series, Subject } from "../../domain/catalog/models";
import { subjectNames } from "../../domain/catalog/models";
import { Button, SearchField, SelectField } from "../../shared/ui";

export interface PaperFilterValue {
  year: string;
  subject: string;
  seriesKey: string;
  query: string;
}

export const EMPTY_PAPER_FILTERS: PaperFilterValue = { year: "", subject: "", seriesKey: "", query: "" };

export const PAPER_ORDER_OPTIONS: { value: PaperOrder; label: string }[] = [
  { value: "series", label: "按系列" },
  { value: "year-desc", label: "新卷优先" },
  { value: "year-asc", label: "旧卷优先" },
  { value: "questions-desc", label: "题目多优先" },
  { value: "questions-asc", label: "题目少优先" },
];

export function PaperFilters({
  value,
  series,
  years,
  onChange,
  order,
  onOrderChange,
  /** Extra content rendered after the counted span (e.g. a result total). */
  trailing,
  queryPlaceholder = "搜索系列、年份或套号",
}: {
  value: PaperFilterValue;
  series: Series[];
  years: number[];
  onChange: (patch: Partial<PaperFilterValue>) => void;
  /** Current ordering; omit together with ``onOrderChange`` to hide the control. */
  order?: PaperOrder;
  onOrderChange?: (order: PaperOrder) => void;
  trailing?: React.ReactNode;
  queryPlaceholder?: string;
}) {
  const hasAny = Boolean(value.year || value.subject || value.seriesKey || value.query);

  return (
    <div className="catalog-tools">
      <SelectField
        label="年份"
        wrapperClassName="tool-field"
        id="filter-year"
        value={value.year}
        onChange={(event) => onChange({ year: event.target.value })}
      >
        <option value="">全部年份</option>
        {years.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="科目"
        wrapperClassName="tool-field"
        id="filter-subject"
        value={value.subject}
        onChange={(event) => onChange({ subject: event.target.value })}
      >
        <option value="">全部科目</option>
        {(Object.keys(subjectNames) as Subject[]).map((key) => (
          <option key={key} value={key}>
            {subjectNames[key]}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="系列"
        wrapperClassName="tool-field"
        id="filter-series"
        value={value.seriesKey}
        onChange={(event) => onChange({ seriesKey: event.target.value })}
      >
        <option value="">全部系列</option>
        {series.map((item) => (
          <option key={item.series_key} value={item.series_key}>
            {item.series_name}
          </option>
        ))}
      </SelectField>
      {onOrderChange && order !== undefined ? (
        <SelectField
          label="排序"
          wrapperClassName="tool-field"
          id="filter-order"
          value={order}
          onChange={(event) => onOrderChange(event.target.value as PaperOrder)}
        >
          {PAPER_ORDER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </SelectField>
      ) : null}
      <SearchField
        value={value.query}
        onChange={(next) => onChange({ query: next })}
        label="搜索"
        placeholder={queryPlaceholder}
      />
      {hasAny ? (
        <Button
          size="sm"
          variant="quiet"
          icon={<X size={14} />}
          onClick={() => onChange({ year: "", subject: "", seriesKey: "", query: "" })}
        >
          清除筛选
        </Button>
      ) : null}
      {trailing}
    </div>
  );
}
