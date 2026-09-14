/**
 * Application providers.
 *
 * One composition point for every cross-cutting concern: data cache, user
 * preferences, notifications. Keeping them together means `main.tsx` stays a
 * three-line bootstrap and tests can mount the same stack with stubs.
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { PreferencesProvider, type Preferences } from "../preferences";
import { ToastProvider } from "../shared/ui";
import { createQueryClient } from "./queryClient";

export function AppProviders({
  children,
  preferences,
  persistPreferences = true,
}: {
  children: ReactNode;
  preferences?: Partial<Preferences>;
  persistPreferences?: boolean;
}) {
  // Created once per mount: recreating the client would drop the whole cache.
  const [client] = useState(createQueryClient);
  return (
    <QueryClientProvider client={client}>
      <PreferencesProvider initial={preferences} persist={persistPreferences}>
        <ToastProvider>{children}</ToastProvider>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}
