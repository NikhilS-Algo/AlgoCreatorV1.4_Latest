import React, { useRef, useCallback } from "react";
import { GripVertical } from "lucide-react";

interface ResizeButtonProps {
  setRightSidebarWidth: React.Dispatch<React.SetStateAction<number>>;
}

const ResizeButton = ({ setRightSidebarWidth }: ResizeButtonProps) => {
  const rightResizeRef = useRef<HTMLDivElement>(null);
  const isRightResizing = useRef(false);
  const handleRightMouseDown = useCallback((e: React.MouseEvent) => {
    isRightResizing.current = true;
    document.addEventListener("mousemove", handleRightMouseMove);
    document.addEventListener("mouseup", handleRightMouseUp);
  }, []);

  const handleRightMouseMove = useCallback((e: MouseEvent) => {
    if (!isRightResizing.current) return;
    const newWidth = Math.max(
      250,
      Math.min(500, window.innerWidth - e.clientX)
    );
    setRightSidebarWidth(newWidth);
  }, []);

  const handleRightMouseUp = useCallback(() => {
    isRightResizing.current = false;
    document.removeEventListener("mousemove", handleRightMouseMove);
    document.removeEventListener("mouseup", handleRightMouseUp);
  }, [handleRightMouseMove]);

  return (
    <div
      ref={rightResizeRef}
      className="absolute top-0 left-0 w-1 h-full cursor-col-resize bg-transparent hover:bg-blue-400 transition-colors"
      onMouseDown={handleRightMouseDown}
    >
      <div className="absolute top-1/2 left-0 transform -translate-y-1/2 -translate-x-1/2">
        <GripVertical className="h-4 w-4 text-gray-300" />
      </div>
    </div>
  );
};

export default ResizeButton;
