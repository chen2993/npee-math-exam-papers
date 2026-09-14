/**
 * Class-name composition helper.
 *
 * Thin wrapper over `clsx` so every component imports one local name; keeping it
 * here means swapping the underlying utility later touches one file.
 */

import clsx, { type ClassValue } from "clsx";

export function classNames(...values: ClassValue[]): string {
  return clsx(values);
}

export type { ClassValue };
