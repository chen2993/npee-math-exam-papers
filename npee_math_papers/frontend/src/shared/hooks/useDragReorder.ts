/**
 * Drag-to-reorder for a vertical list.
 *
 * The composition's print order is the selection order, but the only way to
 * change it was the ▲/▼ buttons: moving a paper twenty places took twenty
 * clicks. This exposes the few handlers a list needs, keeping the drag bookkeeping
 * out of the page component.
 *
 * Native HTML5 drag-and-drop is used (no library) because the app has no other
 * DnD surface and the list is short. Touch devices do not fire these events, so
 * the arrow buttons remain the accessible path; the drag handlers are additive.
 */

import { useCallback, useRef, useState } from "react";

interface DragReorderHandlers {
  onDragStart: (index: number) => void;
  onDragOver: (index: number) => void;
  onDragEnd: () => void;
  onDrop: (index: number) => void;
}

export function useDragReorder(
  onReorder: (from: number, to: number) => void,
): DragReorderHandlers & { draggingIndex: number | null; dropIndex: number | null } {
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [dropIndex, setDropIndex] = useState<number | null>(null);
  /** Mirrors `draggingIndex` for reads inside the drop handler.
   *
   * The handler must not read the state variable through a state updater: React
   * may invoke an updater twice in strict mode, which would fire the reorder
   * callback — and therefore the draft write — twice for one drop.
   */
  const draggingRef = useRef<number | null>(null);

  const onDragStart = useCallback((index: number) => {
    draggingRef.current = index;
    setDraggingIndex(index);
    setDropIndex(index);
  }, []);

  const onDragOver = useCallback((index: number) => {
    setDropIndex(index);
  }, []);

  const onDragEnd = useCallback(() => {
    draggingRef.current = null;
    setDraggingIndex(null);
    setDropIndex(null);
  }, []);

  const onDrop = useCallback(
    (index: number) => {
      const from = draggingRef.current;
      if (from !== null && from !== index) onReorder(from, index);
      draggingRef.current = null;
      setDraggingIndex(null);
      setDropIndex(null);
    },
    [onReorder],
  );

  return { draggingIndex, dropIndex, onDragStart, onDragOver, onDragEnd, onDrop };
}
