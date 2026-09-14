/**
 * The shared TanStack Query client.
 *
 * Defaults are chosen for a local, single-user console backed by a file store:
 * reads are cheap, so a short stale window keeps the UI responsive; retries are
 * limited because a failure here almost always means the API is not running and
 * hammering it only delays the error message.
 */

import { QueryClient } from "@tanstack/react-query";

import { HttpError } from "../infrastructure/http/HttpError";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          // A 4xx means the request itself is wrong; retrying cannot help.
          if (error instanceof HttpError && error.status >= 400 && error.status < 500) return false;
          return failureCount < 2;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}
