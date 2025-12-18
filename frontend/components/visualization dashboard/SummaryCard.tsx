import React, { useEffect, useRef, useState } from "react";

import subfolderSummaries from "@/data/subfolder_summaries.json";

interface SummaryCardProps {
  folderName: string;
}

interface summariesData {
  [key: string]: string;
}

const summariesData: summariesData = subfolderSummaries;

const SummaryCard: React.FC<SummaryCardProps> = ({ folderName }) => {
  const textRef = useRef<HTMLDivElement | null>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const findSummary = (folderName: string) => {
    if (folderName == "ROOT_FOLDER") folderName = "Algo_Org_PPTs";
    for (const path in summariesData) {
      const lastFolderName = path.split("/").filter(Boolean).pop();
      if (lastFolderName === folderName) {
        return summariesData[path];
      }
    }
    return "";
  };

  const summary = findSummary(folderName);


  useEffect(() => {
    const checkOverflow = () => {
      const el = textRef.current;
      if (el) {
        const overflow = el.scrollHeight > el.clientHeight;
        setIsOverflowing(overflow);
      }
    };

    setTimeout(checkOverflow, 0);
  }, [expanded, summary]);

  const processedSummary =
    typeof summary === "string"
      ? summary.replace(/^.*?(\n\n|:)[^a-zA-Z0-9]*/, "")
      : "No Summary Available";

  return (
    <div
      id="summary-card"
      className={`transition-all duration-300 shadow-md rounded-xl border border-transparent bg-white p-4 hover:shadow-xl hover:-translate-y-1 hover:border-blue-500 hover:bg-blue-50 ${
        expanded ? "w-[450px]" : "w-[300px]"
      }`}
    >
      {summary === "No Summary Available" ? (
        <p className="text-red-600 font-semibold">No Summary Available</p>
      ) : (
        <>
          <p className="font-semibold text-gray-800 text-base mb-2">
            Summary of {folderName}:
          </p>

          <div
            ref={textRef}
            className={`text-sm text-gray-600 leading-relaxed transition-all duration-300 ${
              expanded ? "" : "line-clamp-6"
            }`}
            style={
              expanded ? { WebkitLineClamp: "unset", overflow: "visible" } : {}
            }
          >
            {processedSummary}
          </div>

          {(isOverflowing || expanded) && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 text-sm text-blue-600 underline hover:text-blue-800"
            >
              {expanded ? "Show less" : "Read more"}
            </button>
          )}
        </>
      )}
    </div>
  );
};

export default SummaryCard;
