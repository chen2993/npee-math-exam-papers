import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ToastProvider } from "../../shared/ui";
import { PayloadView } from "./PayloadView";

function renderView(payload: Parameters<typeof PayloadView>[0]["payload"], tone: "request" | "response" = "request") {
  return render(
    <ToastProvider>
      <PayloadView title="请求体" payload={payload} tone={tone} />
    </ToastProvider>,
  );
}

describe("PayloadView", () => {
  it("renders parsed JSON as key/value rows", () => {
    renderView({ json: { composition_id: "demo", count: 3 }, bytes: 24 });
    expect(screen.getByText("composition_id")).toBeInTheDocument();
    expect(screen.getByText("demo")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText(/24 字节/)).toBeInTheDocument();
  });

  it("folds deep branches but opens the top levels", async () => {
    const user = userEvent.setup();
    renderView({ json: { outer: { inner: { deep: "value" } } } });
    // Two levels are open by default, so the innermost key starts hidden.
    expect(screen.queryByText("deep")).not.toBeInTheDocument();
    await user.click(screen.getByText("inner"));
    expect(await screen.findByText("deep")).toBeInTheDocument();
  });

  it("explains a binary body instead of showing its bytes", () => {
    renderView({ binary: true, bytes: 119331, content_type: "application/pdf" });
    expect(screen.getByText(/二进制内容/)).toBeInTheDocument();
    // The media type shows in the header meta and again in the explanation, so
    // assert on the explanation rather than a bare match.
    expect(screen.getByText(/二进制内容（application\/pdf）/)).toBeInTheDocument();
    expect(screen.getByText(/119,331 字节/)).toBeInTheDocument();
  });

  it("renders plain text bodies verbatim", () => {
    renderView({ text: "line one\nline two" });
    expect(screen.getByText(/line one/)).toBeInTheDocument();
  });

  it("says so when there is no body", () => {
    renderView({});
    expect(screen.getByText("无内容")).toBeInTheDocument();
  });
});
