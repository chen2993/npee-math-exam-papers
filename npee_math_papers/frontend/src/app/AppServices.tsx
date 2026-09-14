/**
 * The gateway bundle, provided by context.
 *
 * Pages need the catalogue gateway, the draft repository and the export gateway.
 * Passing them through every lazy route as props would couple the route table to
 * each page's signature; a small context keeps the route table uniform and lets
 * tests inject fakes in one place.
 */

import { createContext, useContext, type ReactNode } from "react";

import type { CatalogGateway } from "../application/catalog/ports";
import type { CompositionDraftRepository, CompositionExportGateway } from "../application/composition/ports";

export interface AppServices {
  gateway: CatalogGateway;
  draftRepository: CompositionDraftRepository;
  exportGateway: CompositionExportGateway;
}

const AppServicesContext = createContext<AppServices | null>(null);

export function AppServicesProvider({ services, children }: { services: AppServices; children: ReactNode }) {
  return <AppServicesContext.Provider value={services}>{children}</AppServicesContext.Provider>;
}

export function useAppServices(): AppServices {
  const context = useContext(AppServicesContext);
  if (!context) throw new Error("useAppServices 必须在 AppServicesProvider 内使用");
  return context;
}
