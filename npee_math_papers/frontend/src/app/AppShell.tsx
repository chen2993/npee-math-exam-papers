/**
 * The application root: providers + router.
 *
 * Kept deliberately thin. Anything cross-cutting (data cache, preferences,
 * toasts) is a provider; anything page-specific is behind the router. That is
 * the split that keeps this file short and the shell free of business logic.
 */

import { useState } from "react";
import { HashRouter } from "react-router-dom";

import type { Preferences } from "../preferences";
import { classNames } from "../shared/ui";
import { AppProviders } from "./providers";
import { AppRouter } from "./AppRouter";
import { catalogGateway, compositionDraftRepository, compositionExportGateway } from "./compositionRoot";

export function AppShell({ initialPreferences }: { initialPreferences?: Partial<Preferences> }) {
  // The mobile "drawer" sidebar is deliberately separate from the persisted
  // desktop collapse preference, so opening the menu on a phone does not
  // change the desktop layout.
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <AppProviders preferences={initialPreferences}>
      {/* Hash history: the production build is served by a plain static server. */}
      <HashRouter>
        <div className={classNames("app-root", mobileSidebarOpen && "is-mobile-nav-open")}>
          <AppRouter
            services={{
              gateway: catalogGateway,
              draftRepository: compositionDraftRepository,
              exportGateway: compositionExportGateway,
            }}
            onToggleSidebar={() => setMobileSidebarOpen((open) => !open)}
          />
        </div>
      </HashRouter>
    </AppProviders>
  );
}
