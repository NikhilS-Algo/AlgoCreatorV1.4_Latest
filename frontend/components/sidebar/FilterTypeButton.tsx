import React from "react";
import { Button } from "@/components/ui/button";
import { TimerIcon as Timeline, CalendarIcon } from "lucide-react";

interface FilterTypeButtonProps {
    dateMode: "timeline" | "calendar";
    setDateMode: React.Dispatch<React.SetStateAction<"timeline" | "calendar">>;
}

const FilterTypeButton = ({dateMode, setDateMode}: FilterTypeButtonProps) => {
  return (
    <div className="flex flex-wrap gap-2 items-center justify-center">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setDateMode("timeline")}
        className={`flex-1 px-2 py-2 font-medium transition-all duration-200 shadow-sm ${
          dateMode === "timeline"
            ? "bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 hover:text-white"
            : "bg-white border border-gray-300 text-gray-700 hover:bg-blue-50"
        }`}
      >
        <Timeline className="h-4 w-4 mr-2" />
        Timeline
      </Button>

      <Button
        variant="outline"
        size="sm"
        id="calendar-btn"
        onClick={() => setDateMode("calendar")}
        className={`flex-1 px-2 py-2 text-sm font-medium transition-all duration-200 shadow-sm ${
          dateMode === "calendar"
            ? "bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 hover:text-white"
            : "bg-white border border-gray-300 text-gray-700 hover:bg-blue-50"
        }`}
      >
        <CalendarIcon className="h-4 w-4 mr-2" />
        Calendar
      </Button>
    </div>
  );
};

export default FilterTypeButton;
