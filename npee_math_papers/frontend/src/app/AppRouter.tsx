/**
 * The routed application.
 *
 * Pages are lazily imported so the initial bundle contains only the shell and
 * the first page; the rest arrive on navigation. Each page is wrapped in an
 * error boundary keyed by path, so a failure is contained and retryable.
 */

import { Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { ErrorBoundary } from "../shared/ui";
import { AppServicesProvider, type AppServices } from "./AppServices";
import { CompositionWorkspaceProvider } from "./CompositionWorkspace";
import { AppLayout } from "./AppLayout";
import { DEFAULT_ROUTE, ROUTES } from "./routes";

function RouteFallback() {
  return (
    <div className="route-fallback" role="status">
      <span className="route-fallback-bar" />
      正在打开页面…
    </div>
  );
}

function NotFound() {
  return (
    <div className="not-found surface">
      <span className="eyebrow">404</span>
      <h3>页面不存在</h3>
      <p>请从左侧导航选择一个页面。</p>
    </div>
  );
}

export function AppRouter({
  services,
  onToggleSidebar,
}: {
  services: AppServices;
  onToggleSidebar: () => void;
}) {
  const location = useLocation();

  return (
    <AppServicesProvider services={services}>
      <CompositionWorkspaceProvider repository={services.draftRepository} exportGateway={services.exportGateway}>
      <Routes>
        <Route element={<AppLayout gateway={services.gateway} onToggleSidebar={onToggleSidebar} />}>
          <Route index element={<Navigate to={DEFAULT_ROUTE} replace />} />
          {ROUTES.map((route) => {
            const Page = route.element;
            return (
              <Route
                key={route.path}
                path={route.path.slice(1)}
                element={
                  <ErrorBoundary resetKey={location.pathname}>
                    <Suspense fallback={<RouteFallback />}>
                      <Page />
                    </Suspense>
                  </ErrorBoundary>
                }
              />
            );
          })}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
      </CompositionWorkspaceProvider>
    </AppServicesProvider>
  );
}
