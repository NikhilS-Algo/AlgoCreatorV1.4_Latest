import React, { useEffect, useState } from "react";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import { selectSelectedDateRange } from "@/redux/features/filters/selectedDateRangeSlice";
import { useToast } from "@/hooks/use-toast";
import {
  selectFoldersLoading,
  setFoldersLoading,
} from "@/redux/features/loading/foldersLoadingSlice";
import { setFoldersData } from "@/redux/features/filters/FetchedFoldersSlice";
import { selectSelectedFiles } from "@/redux/features/filters/selectedFilesSlice";
import { getFilesTree } from "./getFiles";

const ApplyDateButton = () => {
  const { toast } = useToast();
  const selectedDates = useAppSelector(selectSelectedDateRange);
  const selectedFiles = useAppSelector(selectSelectedFiles);
  const dispatch = useAppDispatch();
  const [isFirstLoading, setIsFirstLoading] = useState(true);

  const handleApplyDate = async () => {
    if (!selectedDates.from || !selectedDates.to) {
      toast({
        variant: "destructive",
        title: "Missing Information",
        description: "Please select a date range.",
        duration: 2000,
      });
      return;
    }

    dispatch(setFoldersLoading("loading"));
    const folders = getFilesTree(
      selectedDates.from,
      selectedDates.to,
      selectedDates.from,
      selectedDates.to,
      dispatch
    );
    if (folders) {
      dispatch(setFoldersData(folders));
      dispatch(setFoldersLoading("loaded"));
      if(!isFirstLoading) {
        toast({
          variant: "default",
          title: "Dates Applied",
          description: "Your date filter has been successfully applied.",
          duration: 2000,
        });
      }
      setIsFirstLoading(false);
    } else {
      dispatch(setFoldersLoading("error"));
    }
  };

  useEffect(() => {
    handleApplyDate();
  }, []);

  return (
    <button
      onClick={handleApplyDate}
      id="apply-dates-btn"
      className="px-2 py-4 h-7 w-full rounded flex items-center justify-center bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 hover:text-white transition-all duration-200 shadow-sm"
    >
      <span className="text-sm text-white ">Apply Dates</span>
    </button>
  );
};

export default ApplyDateButton;
