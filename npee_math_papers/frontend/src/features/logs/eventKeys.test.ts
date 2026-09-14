import { describe, expect, it } from "vitest";

import type { LogEvent } from "../../domain/catalog/models";
import { eventKeys } from "./LogPageRoute";

function event(ts: string, name: string): LogEvent {
  return {
    ts,
    surface: "http",
    kind: "request",
    name,
    status: "ok",
    status_code: 200,
    duration_ms: 1,
    detail: {},
    request: {},
    response: {},
  };
}

describe("eventKeys", () => {
  it("gives a stable key per event regardless of position", () => {
    // Regression: keys used to include the row index, so the 3-second refresh
    // remounted the list and collapsed expanded rows.
    const older = event("2026-01-01T00:00:00.000Z", "GET /api/papers");
    const newer = event("2026-01-01T00:00:01.000Z", "GET /api/overview");

    const [olderKey] = eventKeys([older, newer]);
    const [, olderKeyAfterNewEvent] = eventKeys([newer, older]);
    expect(olderKeyAfterNewEvent).toBe(olderKey);
  });

  it("disambiguates genuine duplicates without shifting", () => {
    const same = event("2026-01-01T00:00:00.000Z", "GET /api/papers");
    const keys = eventKeys([same, { ...same }]);
    expect(keys[0]).not.toBe(keys[1]);
    // Recomputing over the same input is idempotent.
    expect(eventKeys([same, { ...same }])).toEqual(keys);
  });
});
