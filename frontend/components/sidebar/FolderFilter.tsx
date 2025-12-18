import React from "react";
import { Badge } from "@/components/ui/badge";
import ApplyChangesButton from "./ApplyChangesButton";
import { useAppSelector } from "@/redux/hooks";
import { selectFoldersLoading } from "@/redux/features/loading/foldersLoadingSlice";
import FolderSelection from "./FolderSelection";

const FolderFilter = () => {
  const foldersLoading = useAppSelector(selectFoldersLoading);

  return (
    <div
      id="folder-selection"
      className="bg-white rounded-xl p-5 space-y-2 border border-amber-200/50 shadow-sm mt-2"
    >
      <h4 className="text-sm font-bold text-gray-800 mb-1">Folder Selection</h4>
      {foldersLoading === "loading" && (
        <span className="text-lg font-semibold text-orange-500 mb-1 flex justify-center">
          Fetching Folders...
        </span>
      )}
      {foldersLoading === "error" && (
        <span className="text-lg font-bold text-red-500 mb-1 flex justify-center">
          Error Fetching Folders
        </span>
      )}
      {foldersLoading === "loaded" && (
        <>
          <FolderSelection />
          <ApplyChangesButton />
        </>
      )}
    </div>
  );
};

export default FolderFilter;
