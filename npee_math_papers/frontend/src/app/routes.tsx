/**
 * The route table.
 *
 * One declaration drives both routing and the sidebar menu, so a page can never
 * exist in the navigation without a route (or vice versa) — the pattern taken
 * from ant-design-pro's `config/routes.ts`.
 *
 * Routes use a **hash** history: the production build is served by
 * ``python -m http.server``, which has no SPA fallback, so a path-based deep link
 * would 404 on reload. Hashes are handled entirely client-side and work there.
 */

import { FileArchive, LayoutDashboard, ListTree, ScrollText, Search, Sparkles } from "lucide-react";
import { lazy, type ComponentType } from "react";

// Lazy so each page is a separate chunk; the first paint only ships the shell.
const DashboardPageRoute = lazy(() => import("../features/dashboard/DashboardPageRoute"));
const PaperCatalogPageRoute = lazy(() => import("../features/catalog/PaperCatalogPageRoute"));
const SearchPageRoute = lazy(() => import("../features/search/SearchPageRoute"));
const CompositionPageRoute = lazy(() => import("../features/composition/CompositionPageRoute"));
const ReleasePageRoute = lazy(() => import("../features/release/ReleasePageRoute"));
const LogPageRoute = lazy(() => import("../features/logs/LogPageRoute"));

export interface RouteDefinition {
  /** Hash path without the leading ``#``. */
  path: string;
  /** Sidebar label. */
  label: string;
  /** One-line description shown under the page title. */
  description: string;
  /** Breadcrumb trail (excluding the root). */
  breadcrumb: string[];
  icon: ComponentType<{ size?: number | string }>;
  element: ComponentType;
  /** Group heading in the sidebar; routes with no group render ungrouped. */
  group?: string;
  /** Hidden routes are routable but absent from the sidebar. */
  hidden?: boolean;
}

export const ROUTES: readonly RouteDefinition[] = [
  {
    path: "/dashboard",
    label: "仪表盘",
    description: "题库总览、系列分布与近期活动。",
    breadcrumb: ["工作区", "仪表盘"],
    icon: LayoutDashboard,
    element: DashboardPageRoute,
    group: "工作区",
  },
  {
    path: "/papers",
    label: "套卷",
    description: "按系列、年份、科目筛选套卷并加入组卷。",
    breadcrumb: ["工作区", "套卷"],
    icon: ListTree,
    element: PaperCatalogPageRoute,
    group: "工作区",
  },
  {
    path: "/search",
    label: "题目检索",
    description: "在题干、选项与子问中全文检索题目。",
    breadcrumb: ["工作区", "题目检索"],
    icon: Search,
    element: SearchPageRoute,
    group: "工作区",
  },
  {
    path: "/compose",
    label: "组卷",
    description: "编排套卷、设置版式，编译导出 PDF。",
    breadcrumb: ["构建", "组卷"],
    icon: FileArchive,
    element: CompositionPageRoute,
    group: "构建",
  },
  {
    path: "/release",
    label: "版本清单",
    description: "查看每套卷的内容哈希与库级发布哈希。",
    breadcrumb: ["构建", "版本清单"],
    icon: Sparkles,
    element: ReleasePageRoute,
    group: "构建",
  },
  {
    path: "/logs",
    label: "操作日志",
    description: "统一查看 Agent 的 MCP 调用与前端 HTTP 请求。",
    breadcrumb: ["运维", "操作日志"],
    icon: ScrollText,
    element: LogPageRoute,
    group: "运维",
  },
];

export const DEFAULT_ROUTE = "/dashboard";

/** Visited routes in sidebar order, grouped for the navigation. */
export function routeGroups(): { group: string; routes: RouteDefinition[] }[] {
  const groups: { group: string; routes: RouteDefinition[] }[] = [];
  for (const route of ROUTES) {
    if (route.hidden) continue;
    const name = route.group ?? "其他";
    const existing = groups.find((item) => item.group === name);
    if (existing) existing.routes.push(route);
    else groups.push({ group: name, routes: [route] });
  }
  return groups;
}

export function findRoute(path: string): RouteDefinition | undefined {
  return ROUTES.find((route) => route.path === path);
}
