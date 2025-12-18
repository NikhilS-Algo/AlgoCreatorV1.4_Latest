import React from "react";
import { format } from "date-fns";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import {
  selectSelectedDateRange,
  setSelectedDateRange,
} from "@/redux/features/filters/selectedDateRangeSlice";
import { selectFilesDateRange } from "@/redux/features/filters/filesDateRangeSlice";
import DualRangeSlider from "./DualRangeSlider";

const TimelineDateSelection = () => {
  const dispatch = useAppDispatch();

  const { from: selectedFrom, to: selectedTo } = useAppSelector(
    selectSelectedDateRange
  );

  const { from: filesFrom, to: filesTo } = useAppSelector(
    selectFilesDateRange
  );

  const minTimestamp = new Date(filesFrom).getTime();
  const maxTimestamp = new Date(filesTo).getTime();
  const selectedValue: [number, number] = [
    new Date(selectedFrom).getTime(),
    new Date(selectedTo).getTime(),
  ];

  const handleRangeChange = (newRange: [number, number]) => {
    dispatch(
      setSelectedDateRange({
        from: new Date(newRange[0]).toISOString(),
        to: new Date(newRange[1]).toISOString(),
      })
    );
  };

  const formatTimelineRange = (
    startTimestamp: number,
    endTimestamp: number
  ) => {
    const startDate = new Date(startTimestamp);
    const endDate = new Date(endTimestamp);
    return `${format(startDate, "MMM yyyy")} - ${format(endDate, "MMM yyyy")}`;
  };

  return (
    <div id="timeline-slider">
      <div className="text-sm font-semibold text-gray-800 mb-2">Timeline</div>
      <div className="text-sm text-blue-600 mb-4 font-medium">
        {selectedFrom && selectedTo
          ? formatTimelineRange(
              new Date(selectedFrom).getTime(),
              new Date(selectedTo).getTime()
            )
          : "No dates selected"}
      </div>
      <div className="px-2 py-6">
        <DualRangeSlider
          min={minTimestamp}
          max={maxTimestamp}
          value={selectedValue}
          onValueChange={handleRangeChange}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-4">
          <span>{format(new Date(filesFrom), "MMM yyyy")}</span>
          <span>{format(new Date(filesTo), "MMM yyyy")}</span>
        </div>
      </div>
    </div>
  );
};

export default TimelineDateSelection;
