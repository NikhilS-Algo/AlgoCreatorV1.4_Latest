import React from "react";
import { Button } from "@/components/ui/button";
import { format, subDays, subYears, endOfDay } from "date-fns";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import {
  selectSelectedDateRange,
  setSelectedDateRange,
} from "@/redux/features/filters/selectedDateRangeSlice";
import { selectFilesDateRange } from "@/redux/features/filters/filesDateRangeSlice";

const quickDateFilters = [
  { label: "Last 7 days", value: "7d" },
  { label: "Last 30 days", value: "30d" },
  { label: "Last 90 days", value: "90d" },
  { label: "Last year", value: "1y" },
  { label: "All time", value: "all" },
];

const QuickDateFilters = () => {
  const dispatch = useAppDispatch();
  const { from: selectedFrom, to: selectedTo } = useAppSelector(
    selectSelectedDateRange
  );
  const { from: filesFrom, to: filesTo } = useAppSelector(selectFilesDateRange);
  const handleQuickFilter = (filterType: string) => {
    if (!filesFrom || !filesTo) return;

    const now = endOfDay(new Date());
    let startDate: Date;

    switch (filterType) {
      case "7d":
        startDate = subDays(now, 7);
        break;
      case "30d":
        startDate = subDays(now, 30);
        break;
      case "90d":
        startDate = subDays(now, 90);
        break;
      case "1y":
        startDate = subYears(now, 1);
        break;
      case "all":
        dispatch(
          setSelectedDateRange({
            from: filesFrom,
            to: new Date(Date.now()).toISOString(),
          })
        );
        return; // Exit
      default:
        return;
    }

    const finalStartTimestamp = Math.max(
      startDate.getTime(),
      new Date(filesFrom).getTime()
    );
    dispatch(
      setSelectedDateRange({
        from: new Date(finalStartTimestamp).toISOString(),
        to: now.toISOString(),
      })
    );
  };
  return (
    <div className="grid grid-cols-2 gap-2">
      {quickDateFilters.map((filter) => (
        <Button
          key={filter.value}
          variant="outline"
          size="sm"
          className="text-xs h-8 border-blue-200 text-blue-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700"
          onClick={() => handleQuickFilter(filter.value)}
        >
          {filter.label}
        </Button>
      ))}
    </div>
  );
};

export default QuickDateFilters;
