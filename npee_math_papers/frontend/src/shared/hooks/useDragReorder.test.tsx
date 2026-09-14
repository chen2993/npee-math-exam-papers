import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useDragReorder } from "./useDragReorder";

describe("useDragReorder", () => {
  it("reports a reorder when an item is dropped elsewhere", () => {
    const onReorder = vi.fn();
    const { result } = renderHook(() => useDragReorder(onReorder));

    act(() => result.current.onDragStart(0));
    act(() => result.current.onDragOver(2));
    act(() => result.current.onDrop(2));

    expect(onReorder).toHaveBeenCalledWith(0, 2);
    expect(result.current.draggingIndex).toBeNull();
  });

  it("does not reorder when an item is dropped on itself", () => {
    const onReorder = vi.fn();
    const { result } = renderHook(() => useDragReorder(onReorder));

    act(() => result.current.onDragStart(1));
    act(() => result.current.onDrop(1));

    expect(onReorder).not.toHaveBeenCalled();
  });

  it("clears the drag state when the drag is abandoned", () => {
    const onReorder = vi.fn();
    const { result } = renderHook(() => useDragReorder(onReorder));

    act(() => result.current.onDragStart(0));
    expect(result.current.draggingIndex).toBe(0);
    act(() => result.current.onDragEnd());

    expect(result.current.draggingIndex).toBeNull();
    expect(result.current.dropIndex).toBeNull();
    expect(onReorder).not.toHaveBeenCalled();
  });
});
