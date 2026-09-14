/**
 * Button primitives.
 *
 * One `Button` covers the four roles the app needs (primary, default, quiet,
 * danger) plus an icon-only `IconButton`. Variants and sizes are data, so adding
 * one touches this file only.
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { classNames } from "./classNames";

export type ButtonVariant = "primary" | "default" | "quiet" | "danger";
export type ButtonSize = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "default", size = "md", icon, className, children, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={classNames("button", `button-${variant}`, size === "sm" && "button-sm", className)}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
});

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Accessible label; also rendered as the native tooltip. */
  label: string;
  size?: ButtonSize;
  tone?: "default" | "danger";
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, size = "md", tone = "default", className, children, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      title={label}
      aria-label={label}
      className={classNames("icon-button", `icon-button-${tone}`, size === "sm" && "icon-button-sm", className)}
      {...rest}
    >
      {children}
    </button>
  );
});
