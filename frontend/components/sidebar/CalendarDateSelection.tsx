import React from "react";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import { Calendar as CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { format, startOfDay, endOfDay } from "date-fns";
import { DateRange } from "react-day-picker";

import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import {
  selectSelectedDateRange,
  setSelectedDateRange,
} from "@/redux/features/filters/selectedDateRangeSlice";

const CalendarDateSelection = () => {
  const dispatch = useAppDispatch();
  const { from: fromString, to: toString } = useAppSelector(selectSelectedDateRange);

  const from = fromString ? new Date(fromString) : undefined;
  const to = toString ? new Date(toString) : undefined;

  const selectedDates: DateRange = { from, to };

  const handleDateChange = (range: DateRange | undefined) => {
    if (range?.from && range?.to) {
      dispatch(setSelectedDateRange({
        from: startOfDay(range.from).toISOString(),
        to: endOfDay(range.to).toISOString(),
      }));
    } else if (range?.from) {
      dispatch(setSelectedDateRange({
        from: startOfDay(range.from).toISOString(),
        to: endOfDay(range.from).toISOString(),
      }));
    }
  };

  return (
    <div className="space-y-2">
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="w-full justify-start text-left font-normal border-blue-200 hover:bg-blue-50 overflow-hidden whitespace-nowrap truncate"
          >
            <CalendarIcon className="mr-2 h-4 w-4 text-blue-500" />
            {from ? (
              to ? (
                <>
                  {format(from, "LLL dd, y")} - {format(to, "LLL dd, y")}
                </>
              ) : (
                format(from, "LLL dd, y")
              )
            ) : (
              <span>Pick a date range</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            initialFocus
            mode="range"
            defaultMonth={from}
            selected={selectedDates}
            onSelect={handleDateChange}
            numberOfMonths={2}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default CalendarDateSelection;
