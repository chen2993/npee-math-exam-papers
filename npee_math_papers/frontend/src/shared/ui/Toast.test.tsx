import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ToastProvider, useToast } from "./Toast";

function Trigger() {
  const toast = useToast();
  return (
    <div>
      <button onClick={() => toast.notify("已保存")}>ok</button>
      <button onClick={() => toast.notify("失败了", "error", 0)}>bad</button>
    </div>
  );
}

describe("ToastProvider", () => {
  it("shows a notification and auto-dismisses it", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider defaultDurationMs={40}>
        <Trigger />
      </ToastProvider>,
    );
    await user.click(screen.getByText("ok"));
    expect(screen.getByText("已保存")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("已保存")).not.toBeInTheDocument(), { timeout: 1500 });
  });

  it("keeps a zero-duration toast until dismissed", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    await user.click(screen.getByText("bad"));
    const toaster = screen.getByText("失败了");
    expect(toaster).toBeInTheDocument();
    await user.click(screen.getByLabelText("关闭"));
    expect(screen.queryByText("失败了")).not.toBeInTheDocument();
  });

  it("ignores empty messages", async () => {
    const user = userEvent.setup();
    function Empty() {
      const toast = useToast();
      return <button onClick={() => toast.notify("   ")}>empty</button>;
    }
    render(
      <ToastProvider>
        <Empty />
      </ToastProvider>,
    );
    await user.click(screen.getByText("empty"));
    expect(document.querySelectorAll(".toast")).toHaveLength(0);
  });
});
