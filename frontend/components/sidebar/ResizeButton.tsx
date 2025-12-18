import React, { useCallback, useRef } from "react";
import { GripVertical } from "lucide-react";

interface ResizeButtonProps {
  setLeftSidebarWidth: React.Dispatch<React.SetStateAction<number>>;
}


const ResizeButton = ({setLeftSidebarWidth}: ResizeButtonProps) => {
  const leftResizeRef = useRef<HTMLDivElement>(null);
  const isLeftResizing = useRef(false);
  const handleLeftMouseDown = useCallback((e: React.MouseEvent) => {
    isLeftResizing.current = true;
    document.addEventListener("mousemove", handleLeftMouseMove);
    document.addEventListener("mouseup", handleLeftMouseUp);
  }, []);

  const handleLeftMouseMove = useCallback((e: MouseEvent) => {
    if (!isLeftResizing.current) return;
    const newWidth = Math.max(250, Math.min(500, e.clientX));
    setLeftSidebarWidth(newWidth);
  }, []);

  const handleLeftMouseUp = useCallback(() => {
    isLeftResizing.current = false;
    document.removeEventListener("mousemove", handleLeftMouseMove);
    document.removeEventListener("mouseup", handleLeftMouseUp);
  }, [handleLeftMouseMove]);

  return (
    <div
      ref={leftResizeRef}
      className="absolute top-0 right-0 w-1 h-full cursor-col-resize bg-transparent hover:bg-blue-400 transition-colors"
      onMouseDown={handleLeftMouseDown}
    >
      <div className="absolute top-1/2 right-0 transform -translate-y-1/2 translate-x-1/2">
        <GripVertical className="h-4 w-4 text-gray-300" />
      </div>
    </div>
  );
};

export default ResizeButton;
