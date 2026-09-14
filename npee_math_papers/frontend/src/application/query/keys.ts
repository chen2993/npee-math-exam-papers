/**
 * Central query-key factory.
 *
 * Every cache entry is addressed through this object so invalidation is exact
 * (e.g. after a compile job finishes, invalidate only `jobs`). Scattering string
 * literals across hooks is what makes cache invalidation unreliable.
 */

import type { BundleQuery, PaperQuery } from "../catalog/ports";

export const queryKeys = {
  all: ["npee"] as const,
  health: () => [...queryKeys.all, "health"] as const,
  overview: () => [...queryKeys.all, "overview"] as const,
  series: () => [...queryKeys.all, "series"] as const,
  bundles: (query: BundleQuery) => [...queryKeys.all, "bundles", query] as const,
  papers: (query: PaperQuery) => [...queryKeys.all, "papers", query] as const,
  paper: (seriesKey: string, year: number, subject: string, paperNo: number) =>
    [...queryKeys.all, "paper", seriesKey, year, subject, paperNo] as const,
  search: (query: string, seriesKeys?: string[], subjects?: string[]) =>
    [...queryKeys.all, "search", query, seriesKeys ?? [], subjects ?? []] as const,
  release: () => [...queryKeys.all, "release"] as const,
  logs: (filters: Record<string, unknown>) => [...queryKeys.all, "logs", filters] as const,
  jobs: (limit: number) => [...queryKeys.all, "jobs", limit] as const,
  job: (jobId: string) => [...queryKeys.all, "job", jobId] as const,
};
