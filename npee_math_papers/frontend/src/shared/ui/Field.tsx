/**
 * Form field primitives: labelled inputs, selects and checkboxes.
 *
 * Each control is wrapped with its own label and hint so pages declare intent
 * (`<Select label="页面">`) instead of repeating markup and aria wiring.
 */

import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { classNames } from "./classNames";

interface FieldShellProps {
  label: string;
  hint?: ReactNode;
  controlId: string;
  children: ReactNode;
  className?: string;
}

function FieldShell({ label, hint, controlId, children, className }: FieldShellProps) {
  return (
    <div className={classNames("field", className)}>
      <label className="field-label" htmlFor={controlId}>
        {label}
      </label>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </div>
  );
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: ReactNode;
  wrapperClassName?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { label, hint, wrapperClassName, className, id, ...rest },
  ref,
) {
  const generated = useId();
  const controlId = id ?? generated;
  return (
    <FieldShell label={label} hint={hint} controlId={controlId} className={wrapperClassName}>
      <input ref={ref} id={controlId} className={classNames("field-control", className)} {...rest} />
    </FieldShell>
  );
});

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: ReactNode;
  wrapperClassName?: string;
}

export const TextAreaField = forwardRef<HTMLTextAreaElement, TextAreaFieldProps>(function TextAreaField(
  { label, hint, wrapperClassName, className, id, ...rest },
  ref,
) {
  const generated = useId();
  const controlId = id ?? generated;
  return (
    <FieldShell label={label} hint={hint} controlId={controlId} className={wrapperClassName}>
      <textarea ref={ref} id={controlId} className={classNames("field-control", className)} {...rest} />
    </FieldShell>
  );
});

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: ReactNode;
  wrapperClassName?: string;
  children: ReactNode;
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(function SelectField(
  { label, hint, wrapperClassName, className, id, children, ...rest },
  ref,
) {
  const generated = useId();
  const controlId = id ?? generated;
  return (
    <FieldShell label={label} hint={hint} controlId={controlId} className={wrapperClassName}>
      <select ref={ref} id={controlId} className={classNames("field-control", className)} {...rest}>
        {children}
      </select>
    </FieldShell>
  );
});

export function CheckField({
  label,
  checked,
  onChange,
  disabled,
  className,
}: {
  label: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <label className={classNames("check-field", disabled && "is-disabled", className)}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}
