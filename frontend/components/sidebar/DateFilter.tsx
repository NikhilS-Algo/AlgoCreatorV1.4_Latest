import React, { useEffect, useState } from "react";
import FilterTypeButton from "./FilterTypeButton";
import ApplyDateButton from "./ApplyDateButton";
import CalendarDateSelection from "./CalendarDateSelection";
import TimelineDateSelection from "./TimelineDateSelection";
import QuickDateFilters from "./QuickDateFilters";
import { format } from "date-fns";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import {
  selectSelectedDateRange,
  setSelectedDateRange,
} from "@/redux/features/filters/selectedDateRangeSlice";
import { setFromFileDate } from "@/redux/features/filters/filesDateRangeSlice";
import {setSelectedFromDate} from "@/redux/features/filters/selectedDateRangeSlice";
import { getMinDate } from "./getMinMaxDates";

const DateFilter = () => {
  const dispatch = useAppDispatch();
  const [datesLoaded, setDatesLoaded] = useState<boolean>(false);
  const [dateMode, setDateMode] = useState<"timeline" | "calendar">("timeline");
  const { from: selectedFrom, to: selectedTo } = useAppSelector(
    selectSelectedDateRange
  );

  const formatDateRange = (startTimestamp: number, endTimestamp: number) => {
    const startDate = new Date(startTimestamp);
    const endDate = new Date(endTimestamp);
    return `${format(startDate, "MMM d, yyyy")} - ${format(
      endDate,
      "MMM d, yyyy"
    )}`;
  };

  useEffect(() => {
    const minDate = getMinDate();
    if (minDate) {
      dispatch(setFromFileDate(minDate.toISOString()));
      dispatch(setSelectedFromDate(minDate.toISOString()));
      setDatesLoaded(true);
    }
  }, [])

  return (
    <div className="bg-white rounded-xl p-5 space-y-4 border border-blue-200/50 shadow-sm">
      {!datesLoaded ?  <div className="flex w-full justify-center font-semibold text-red-500">Loading dates...</div> : 
        <>
      <div className="border-l-4 border-blue-500 pl-4">
        <h4 className="text-sm font-bold text-gray-800 mb-1">
          Date Range Selection
        </h4>
        <div className="text-xs text-blue-600">
          {formatDateRange(
            new Date(selectedFrom).getTime(),
            new Date(selectedTo).getTime()
          )}
        </div>
      </div>
      <FilterTypeButton dateMode={dateMode} setDateMode={setDateMode} />
      {dateMode === "calendar" && <CalendarDateSelection />}
      {dateMode === "timeline" && (
        <div className="space-y-4">
          <TimelineDateSelection />
          <QuickDateFilters />
        </div>
      )}
      <ApplyDateButton />
      </>
    }
    </div>
  );
};

export default DateFilter;
