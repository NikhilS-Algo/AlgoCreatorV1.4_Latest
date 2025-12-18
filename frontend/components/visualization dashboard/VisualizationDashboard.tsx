import React, { useEffect, useState } from "react";
import Stats from "./Stats";
import TopTags from "./TopTags";
import SunburstChart from "./SunburstChart";
import SummaryCard from "./SummaryCard";


interface VisualizationDashboardProps {
  parentWidth: number;
}

const VisualizationDashboard = ({
  parentWidth,
}: VisualizationDashboardProps) => {
  const [focusedFolderName, setFocusedFolderName] = useState<string>("");

  return parentWidth > 950 ? (
    <div className="w-full h-full overflow-auto">
        <Stats />
      <div
        className="flex items-center justify-center gap-10"
      >
        <div className="" id='sunburst-chart'>
          <SunburstChart focusedFolderName={focusedFolderName} setFocusedFolderName={setFocusedFolderName} />
        </div>
        <div className="flex flex-col items-center gap-10">
          <SummaryCard folderName={focusedFolderName}/>
          <TopTags />
        </div>
      </div>
    </div>
  ) : parentWidth > 700 ? (
    <div className="w-full h-full overflow-auto">
        <Stats />
      <div
        className="flex flex-col gap-5 items-center justify-center"
      >
        <div className="">
          <SunburstChart focusedFolderName={focusedFolderName} setFocusedFolderName={setFocusedFolderName} />
        </div>
        <div className="flex items-start gap-10 w-full px-10">
          <SummaryCard folderName={focusedFolderName}/>
          <TopTags />
        </div>
      </div>
    </div>
  ) : (
    <div className="w-full h-full overflow-auto">
        <Stats />
      <div
        className="flex flex-col items-center justify-center"
      >
        <div className="">
          <SunburstChart focusedFolderName={focusedFolderName} setFocusedFolderName={setFocusedFolderName}/>
        </div>
        <div className="flex flex-col items-center gap-10 px-10">
          <SummaryCard folderName={focusedFolderName}/>
          <div className="w-full">
          <TopTags />
          </div>
        </div>
      </div>
    </div>
  );
};

export default VisualizationDashboard;
