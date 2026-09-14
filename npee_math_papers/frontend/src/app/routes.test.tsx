import { describe, expect, it } from "vitest";

import { DEFAULT_ROUTE, ROUTES, findRoute, routeGroups } from "./routes";

describe("route table", () => {
  it("has a unique, absolute path per route", () => {
    const paths = ROUTES.map((route) => route.path);
    expect(new Set(paths).size).toBe(paths.length);
    expect(paths.every((path) => path.startsWith("/"))).toBe(true);
  });

  it("declares a default route that exists", () => {
    expect(findRoute(DEFAULT_ROUTE)).toBeTruthy();
  });

  it("groups every visible route under a heading", () => {
    const grouped = routeGroups();
    const covered = grouped.flatMap((group) => group.routes.map((route) => route.path));
    const visible = ROUTES.filter((route) => !route.hidden).map((route) => route.path);
    expect(covered.sort()).toEqual(visible.sort());
    expect(grouped.every((group) => group.group.length > 0)).toBe(true);
  });

  it("gives every route a label, description and breadcrumb", () => {
    for (const route of ROUTES) {
      expect(route.label.length).toBeGreaterThan(0);
      expect(route.description.length).toBeGreaterThan(0);
      expect(route.breadcrumb.length).toBeGreaterThan(0);
      expect(route.breadcrumb.at(-1)).toBe(route.label);
    }
  });
});
