import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SearchField } from "./SearchField";

describe("SearchField", () => {
  it("keeps typing instant but commits once the user pauses", async () => {
    // The search runs on the server, so one request per keystroke would be a
    // request storm; the control must coalesce a burst into one commit.
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchField value="" onChange={onChange} delayMs={40} />);

    await user.type(screen.getByLabelText("搜索"), "张宇");
    expect(onChange).not.toHaveBeenCalled();
    // The typed text is visible immediately, before any commit.
    expect(screen.getByLabelText("搜索")).toHaveValue("张宇");

    await vi.waitFor(() => expect(onChange).toHaveBeenCalledTimes(1), { timeout: 1500 });
    expect(onChange).toHaveBeenCalledWith("张宇");
  });

  it("commits immediately on Enter", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchField value="" onChange={onChange} delayMs={5000} />);
    await user.type(screen.getByLabelText("搜索"), "级数{Enter}");
    expect(onChange).toHaveBeenCalledWith("级数");
  });

  it("adopts an external value so 'clear filters' empties the box", async () => {
    const onChange = vi.fn();
    const { rerender } = render(<SearchField value="张宇" onChange={onChange} delayMs={40} />);
    expect(screen.getByLabelText("搜索")).toHaveValue("张宇");
    rerender(<SearchField value="" onChange={onChange} delayMs={40} />);
    await vi.waitFor(() => expect(screen.getByLabelText("搜索")).toHaveValue(""));
  });

  it("does not fire a commit when nothing changed", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchField value="" onChange={onChange} delayMs={20} />);
    await user.click(screen.getByLabelText("搜索"));
    await new Promise((resolve) => setTimeout(resolve, 120));
    expect(onChange).not.toHaveBeenCalled();
  });
});
