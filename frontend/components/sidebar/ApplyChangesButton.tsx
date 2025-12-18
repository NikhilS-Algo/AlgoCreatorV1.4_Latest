"use client";
import React from "react";
import { selectSelectedFiles } from "@/redux/features/filters/selectedFilesSlice";
import { selectSelectedDateRange } from "@/redux/features/filters/selectedDateRangeSlice";
import { useAppSelector } from "@/redux/hooks";
import { useToast } from "@/hooks/use-toast";

const ApplyChangesButton = () => {
  const selectedFiles = useAppSelector(selectSelectedFiles);
  const { toast } = useToast();
  const selectedDates = useAppSelector(selectSelectedDateRange);

  const handleApplyChanges = async () => {
    try {
      const res = await fetch("/v4beta/api/update-filters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_files: selectedFiles,
          date_range: {
            creation_start: selectedDates.from,
            creation_end: selectedDates.to,
            modification_start: selectedDates.from,
            modification_end: selectedDates.to
          }
        }),
      });

      const data = await res.json();

      if (res.ok) {
        toast({
          variant: "default",
          title: "Changes Applied",
          description: "Your selections have been successfully applied.",
          duration: 2000,
        });
      } else {
        toast({
          variant: "destructive",
          title: "API Error",
          description: data.error || "Failed to apply changes.",
          duration: 2000,
        });
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Network Error",
        description: String(error),
        duration: 2000,
      });
    }
  };

  return (
    <button
      className="px-2 py-4 h-7 w-full rounded flex items-center justify-center bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 hover:text-white transition-all duration-200 shadow-sm"
      onClick={handleApplyChanges}
    >
      <span className="text-sm text-white">Apply Changes</span>
    </button>
  );
};

export default ApplyChangesButton;
