import React, { useState, useRef, useCallback } from "react";
import { useAppDispatch } from "@/redux/hooks";

interface DualRangeSliderProps {
  min: number;
  max: number;
  value: [number, number];
  onValueChange: (value: [number, number]) => void;
  className?: string;
}

const DualRangeSlider = ({
  min,
  max,
  value,
  onValueChange,
  className,
}: DualRangeSliderProps) => {
  const sliderRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState<"start" | "end" | null>(null);
  const [lastInteracted, setLastInteracted] = useState<"start" | "end">("end");

  // Helper function to get the percentage position of a value
  const getPercentage = (val: number) => ((val - min) / (max - min)) * 100;

  // Handles mouse down event on a slider handle
  const handleMouseDown = (type: "start" | "end") => (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(type);
    setLastInteracted(type);
  };

  // Handles click on the slider bar to jump a handle to that position
  const handleBarClick = (e: React.MouseEvent) => {
    if (isDragging || !sliderRef.current) return;

    e.preventDefault();
    e.stopPropagation();

    const rect = sliderRef.current.getBoundingClientRect();
    const percentage = Math.max(
      0,
      Math.min(100, ((e.clientX - rect.left) / rect.width) * 100)
    );
    const newValue = min + (percentage / 100) * (max - min);

    // Determine which handle is closer to the click point
    const startPercentage = getPercentage(value[0]);
    const endPercentage = getPercentage(value[1]);
    const distanceToStart = Math.abs(percentage - startPercentage);
    const distanceToEnd = Math.abs(percentage - endPercentage);

    if (distanceToStart < distanceToEnd) {
      // Move the start handle
      const maxStart = value[1] - (max - min) * 0.001; // Minimum separation
      onValueChange([Math.min(newValue, maxStart), value[1]]);
      setLastInteracted("start");
    } else {
      // Move the end handle
      const minEnd = value[0] + (max - min) * 0.001; // Minimum separation
      onValueChange([value[0], Math.max(newValue, minEnd)]);
      setLastInteracted("end");
    }
  };

  // Handles mouse move event to drag the handles
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !sliderRef.current) return;

      const rect = sliderRef.current.getBoundingClientRect();
      const percentage = Math.max(
        0,
        Math.min(100, ((e.clientX - rect.left) / rect.width) * 100)
      );
      const newValue = min + (percentage / 100) * (max - min);

      if (isDragging === "start") {
        const maxStart = value[1] - (max - min) * 0.001; // Minimum separation
        onValueChange([Math.min(newValue, maxStart), value[1]]);
      } else {
        const minEnd = value[0] + (max - min) * 0.001; // Minimum separation
        onValueChange([value[0], Math.max(newValue, minEnd)]);
      }
    },
    [isDragging, min, max, value, onValueChange]
  );

  // Handles mouse up event to stop dragging
  const handleMouseUp = useCallback(() => {
    setIsDragging(null);
  }, []);

  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Check if handles are overlapping
  const startPercentage = getPercentage(value[0]);
  const endPercentage = getPercentage(value[1]);
  const isOverlapping = Math.abs(endPercentage - startPercentage) < 10;

  // Determine z-index based on overlap and last interaction
  const getHandleZIndex = (handleType: "start" | "end") => {
    if (isDragging === handleType) return "z-50"; // Highest for dragging
    if (!isOverlapping) return "z-30"; // Normal when not overlapping

    // When overlapping, the last interacted handle goes to the back, the other to the front
    if (lastInteracted === handleType) return "z-10"; // Back
    return "z-40"; // Front
  };

  return (
    <div className={`relative h-6 ${className}`}>
      <div
        ref={sliderRef}
        className="absolute top-1/2 transform -translate-y-1/2 w-full h-2 bg-gray-200 rounded-full cursor-pointer select-none"
        onClick={handleBarClick}
        style={{ userSelect: "none" }}
      >
        {/* Selected range */}
        <div
          className="absolute h-3 bg-gradient-to-r from-blue-400 via-emerald-400 to-teal-500 rounded-full pointer-events-none transition-all duration-300 ease-out shadow-sm"
          style={{
            left: `${startPercentage}%`,
            width: `${endPercentage - startPercentage}%`,
          }}
        />

        {/* Start handle */}
        <div
          className={`absolute w-6 h-6 bg-white border-2 border-blue-400 rounded-full cursor-grab active:cursor-grabbing transform -translate-y-1/2 -translate-x-1/2 hover:scale-125 transition-all duration-300 ease-out shadow-lg hover:border-blue-500 ${getHandleZIndex(
            "start"
          )} ${
            isDragging === "start" ? "scale-125 border-blue-500 shadow-xl" : ""
          }`}
          style={{
            left: `${Math.max(3, Math.min(97, startPercentage))}%`,
            top: "50%",
          }}
          onMouseDown={handleMouseDown("start")}
        />

        {/* End handle */}
        <div
          className={`absolute w-6 h-6 bg-white border-2 border-emerald-400 rounded-full cursor-grab active:cursor-grabbing transform -translate-y-1/2 -translate-x-1/2 hover:scale-125 transition-all duration-300 ease-out shadow-lg hover:border-emerald-500 ${getHandleZIndex(
            "end"
          )} ${
            isDragging === "end" ? "scale-125 border-emerald-500 shadow-xl" : ""
          }`}
          style={{
            left: `${Math.max(3, Math.min(97, endPercentage))}%`,
            top: "50%",
          }}
          onMouseDown={handleMouseDown("end")}
        />
      </div>
    </div>
  );
};

export default DualRangeSlider;
