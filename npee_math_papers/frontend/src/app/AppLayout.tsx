/**
 * The application frame: sidebar, header and the routed content area.
 *
 * The layout owns chrome only. It reads the current route to derive the title and
 * breadcrumb, and renders ``<Outlet/>``; every page owns its own data and
 * actions. That split is what removes the old god component: the shell no longer
 * knows how to export or compile anything.
 */

import { ChevronRight, Menu, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useEffect, useMemo } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useOverview } from "../application/query/hooks";
import { usePreferences } from "../preferences";
import { useHotkeys, type Hotkey } from "../shared/hooks/useHotkeys";
import { IconButton, classNames } from "../shared/ui";
import type { CatalogGateway } from "./compositionRoot";
import { PreferencesMenu } from "../features/preferences/PreferencesMenu";
import { ShortcutHelp } from "../features/preferences/ShortcutHelp";
import { findRoute, routeGroups } from "./routes";

export function AppLayout({ gateway, onToggleSidebar }: { gateway: CatalogGateway; onToggleSidebar: () => void }) {
  const { preferences, update } = usePreferences();
  const location = useLocation();
  const navigate = useNavigate();
  const overview = useOverview(gateway);
  const route = findRoute(location.pathname);
  const collapsed = preferences.sidebarCollapsed;

  // Navigation should always start at the top of the new page.
  useEffect(() => {
    document.querySelector(".content-scroll")?.scrollTo({ top: 0 });
  }, [location.pathname]);

  // Speed keys for the two most common actions (search, jump to a page) plus
  // collapse. ``/`` mirrors the convention of GitHub, Slack and most consoles.
  const hotkeys = useMemo<Hotkey[]>(
    () => [
      { key: "/", handler: () => navigate("/search") },
      { key: "[", handler: () => update({ sidebarCollapsed: !collapsed }) },
      { key: "g", meta: true, handler: () => navigate("/dashboard") },
      { key: "p", meta: true, shift: true, handler: () => navigate("/papers") },
      { key: "e", meta: true, shift: true, handler: () => navigate("/compose") },
    ],
    [navigate, update, collapsed],
  );
  useHotkeys(hotkeys);

  const stats = overview.data?.stats;
  const statusText = overview.isLoading
    ? "正在读取题库"
    : overview.isError
      ? "题库不可用"
      : `${stats?.papers ?? 0} 套 · ${stats?.questions ?? 0} 题`;

  return (
    <div className={classNames("app-shell", collapsed && "is-sidebar-collapsed")}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <button
            type="button"
            className="brand-mark"
            onClick={() => update({ sidebarCollapsed: !collapsed })}
            title={collapsed ? "展开侧栏" : "收起侧栏"}
            aria-label={collapsed ? "展开侧栏" : "收起侧栏"}
          >
            N
          </button>
          <span className="brand-name">
            <strong>NPEE</strong>
            <small>数学试卷库</small>
          </span>
        </div>

        <nav className="sidebar-nav" aria-label="主导航">
          {routeGroups().map((group) => (
            <div className="nav-group" key={group.group}>
              <p className="nav-label">{group.group}</p>
              {group.routes.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    title={item.label}
                    className={({ isActive }) => classNames("nav-item", isActive && "is-active")}
                  >
                    <Icon size={17} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="system-card">
            <span className={classNames("system-dot", overview.isError && "is-error")} />
            <div>
              <strong>题库服务</strong>
              <small>{statusText}</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="app-header">
          <div className="header-context">
            <IconButton label="切换侧栏" className="mobile-menu" onClick={onToggleSidebar}>
              <Menu size={19} />
            </IconButton>
            <IconButton
              label={collapsed ? "展开侧栏" : "收起侧栏"}
              className="desktop-collapse"
              onClick={() => update({ sidebarCollapsed: !collapsed })}
            >
              {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
            </IconButton>
            <div className="header-title">
              {preferences.showBreadcrumb ? (
                <nav className="breadcrumb" aria-label="面包屑">
                  {(route?.breadcrumb ?? ["工作区"]).map((part, index, all) => (
                    <span key={part} className="breadcrumb-part">
                      {part}
                      {index < all.length - 1 ? <ChevronRight size={12} /> : null}
                    </span>
                  ))}
                </nav>
              ) : null}
              <h1>{route?.label ?? "NPEE"}</h1>
            </div>
          </div>
          <div className="header-actions">
            <span className={classNames("server-status", overview.isError && "is-error")}>
              <span className="status-pulse" />
              {statusText}
            </span>
            <ShortcutHelp />
            <PreferencesMenu />
          </div>
        </header>

        <div className="content-scroll">
          <div className="content-wrap">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
