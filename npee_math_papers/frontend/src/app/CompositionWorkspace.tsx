/**
 * The composition workspace, provided app-wide.
 *
 * Drafts are shared state: adding a paper on the catalogue page must be visible
 * on the compose page, and both must be the same object. Creating the workspace
 * per page would give each page its own copy that overwrites the other on save,
 * so it is mounted once here and consumed via {@link useWorkspace}.
 *
 * The in-flight compile lives here too, for the same reason: a typeset run takes
 * minutes, so the user will navigate away, and the progress and result must still
 * be there when they come back. Holding it in the compose page instead would end
 * the polling interval on unmount and lose the finished artifacts.
 */

import { createContext, useContext, type ReactNode } from "react";

import { useCompileFlow } from "../application/composition/useCompileFlow";
import { useCompositionWorkspace } from "../application/composition/useCompositionWorkspace";
import type { CompositionDraftRepository, CompositionExportGateway } from "../application/composition/ports";

type Workspace = ReturnType<typeof useCompositionWorkspace>;
type Compile = ReturnType<typeof useCompileFlow>;

const WorkspaceContext = createContext<Workspace | null>(null);
/**
 * The compile job lives in its own context.
 *
 * It changes on every poll while a job runs, so folding it into the workspace
 * value would re-render every page that reads a draft — including the paper
 * table with hundreds of rows — twice a second for no reason. Only the compose
 * page and the progress panel subscribe here.
 */
const CompileContext = createContext<Compile | null>(null);

export function CompositionWorkspaceProvider({
  repository,
  exportGateway,
  children,
}: {
  repository: CompositionDraftRepository;
  exportGateway: CompositionExportGateway;
  children: ReactNode;
}) {
  const workspace = useCompositionWorkspace(repository);
  const compile = useCompileFlow(exportGateway);
  return (
    <WorkspaceContext.Provider value={workspace}>
      <CompileContext.Provider value={compile}>{children}</CompileContext.Provider>
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): Workspace {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error("useWorkspace 必须在 CompositionWorkspaceProvider 内使用");
  return context;
}

/**
 * The app-wide compile job, so it survives leaving the compose page.
 *
 * Kept separate from {@link useWorkspace} so a running job does not re-render
 * pages that only care about the draft.
 */
export function useCompile(): Compile {
  const context = useContext(CompileContext);
  if (!context) throw new Error("useCompile 必须在 CompositionWorkspaceProvider 内使用");
  return context;
}
