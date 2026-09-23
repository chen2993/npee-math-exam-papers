/**
 * Server-state hooks.
 *
 * Every read goes through TanStack Query, which owns caching, loading and error
 * state, retries and refetching. That replaces the per-page
 * ``useEffect + useState + AbortController`` boilerplate and gives one place to
 * tune staleness.
 *
 * Query functions receive the ``AbortSignal`` from the query client, so an
 * unmounted page cancels its in-flight request exactly as before.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { BundleQuery, CatalogGateway, PaperQuery } from "../catalog/ports";
import type { LogQuery } from "../../domain/catalog/models";
import { queryKeys } from "./keys";

export function useOverview(gateway: CatalogGateway) {
  return useQuery({
    queryKey: queryKeys.overview(),
    queryFn: ({ signal }) => gateway.overview(signal),
  });
}

export function useBundles(gateway: CatalogGateway, query: BundleQuery = {}) {
  return useQuery({
    queryKey: queryKeys.bundles(query),
    queryFn: ({ signal }) => gateway.listBundles(query, signal),
  });
}

export function usePapers(gateway: CatalogGateway, query: PaperQuery) {
  return useQuery({
    queryKey: queryKeys.papers(query),
    queryFn: ({ signal }) => gateway.listPapers(query, signal),
    // Keep the previous page visible while the next one loads, so paging does
    // not flash an empty table.
    placeholderData: (previous) => previous,
  });
}

export function usePaperDetail(
  gateway: CatalogGateway,
  ref: { seriesKey: string; year: number; subject: string; paperNo: number } | null,
) {
  return useQuery({
    queryKey: ref
      ? queryKeys.paper(ref.seriesKey, ref.year, ref.subject, ref.paperNo)
      : [...queryKeys.all, "paper", "none"],
    queryFn: ({ signal }) => gateway.getPaper(ref!.seriesKey, ref!.year, ref!.subject, ref!.paperNo, true, signal),
    enabled: ref !== null,
  });
}

export function useReleaseManifest(gateway: CatalogGateway) {
  return useQuery({
    queryKey: queryKeys.release(),
    queryFn: ({ signal }) => gateway.releaseManifest(signal),
    // The manifest only changes when the library is rebuilt; keep it fresh for a
    // while to avoid re-downloading hundreds of hashes on every visit.
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogs(gateway: CatalogGateway, filters: LogQuery, refreshSeconds: number) {
  return useQuery({
    queryKey: queryKeys.logs(filters as Record<string, unknown>),
    queryFn: ({ signal }) => gateway.listLogs(filters, signal),
    refetchInterval: refreshSeconds > 0 ? refreshSeconds * 1000 : false,
    refetchIntervalInBackground: false,
  });
}

export function useClearLogs(gateway: CatalogGateway) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => gateway.clearLogs(),
    onSuccess: () => client.invalidateQueries({ queryKey: [...queryKeys.all, "logs"] }),
  });
}
