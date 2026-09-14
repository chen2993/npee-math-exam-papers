import { HttpCatalogGateway } from "../infrastructure/http/HttpCatalogGateway";
import { HttpCompositionExportGateway } from "../infrastructure/http/HttpCompositionExportGateway";
import { BrowserCompositionDraftRepository } from "../infrastructure/storage/BrowserCompositionDraftRepository";

export const catalogGateway = new HttpCatalogGateway();
export const compositionExportGateway = new HttpCompositionExportGateway();
export const compositionDraftRepository = new BrowserCompositionDraftRepository();

export type { CatalogGateway } from "../application/catalog/ports";
export type { CompositionDraftRepository, CompositionExportGateway } from "../application/composition/ports";
