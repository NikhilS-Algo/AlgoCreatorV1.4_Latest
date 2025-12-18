import React, { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ResizeButton from "./ResizeButton";

import PPTCard from "./PPTCard";
import { useAppSelector } from "@/redux/hooks";
import { selectPresentations } from "@/redux/features/outputs/presentationsSlice";
import {
  ArrowDownWideNarrowIcon,
  ArrowUpWideNarrowIcon,
  BarChart3,
} from "lucide-react";

interface RightSidebarProps {
  rightSidebarOpen: boolean;
  rightSidebarWidth: number;
  setRightSidebarWidth: React.Dispatch<React.SetStateAction<number>>;
}

const RightSidebar = ({
  rightSidebarOpen,
  rightSidebarWidth,
  setRightSidebarWidth,
}: RightSidebarProps) => {
  const presentations = useAppSelector(selectPresentations);
  const [isLatestFirst, setIsLatestFirst] = useState(true);

  const sortedPresentations = [...presentations].sort((a, b) => {
    const dateA = new Date(a.creation_date).getTime();
    const dateB = new Date(b.creation_date).getTime();

    if (isLatestFirst) {
      return dateB - dateA; // Latest first
    } else {
      return dateA - dateB; // Oldest first
    }
  });

  const handleSortToggle = () => {
    setIsLatestFirst(!isLatestFirst);
  };

  return (
    <div
      className="bg-blue-50 border-l border-gray-200 flex flex-col relative shadow-sm"
      style={{ width: rightSidebarWidth }}
    >
      <div className="p-4 border-b border-gray-200 ">
        <div className="flex items-center justify-between m-1">
          <h2 className="text-lg font-bold ">Outputs</h2>
        </div>
      </div>
      <Tabs
        defaultValue="presentations"
        className="flex-1 flex flex-col overflow-y-auto"
        id="outputs-panel"
      >
        <TabsList className="grid max-w-full grid-cols-1 mx-4 my-2 bg-white border border-blue-400">
          <TabsTrigger
            value="presentations"
            className="data-[state=active]:bg-white data-[state=active]:text-blue-600 m-0"
          >
            Presentations
          </TabsTrigger>
        </TabsList>
        <TabsContent value="presentations" className="flex-1 overflow-y-auto">
          {presentations.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center px-4 space-y-4">
              <BarChart3 className="h-16 w-16 text-blue-300" />
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No presentations generated yet
                </h3>
                <p className="text-sm text-blue-600">
                  Chat with the AI to create presentations
                </p>
              </div>
            </div>
          )}

          {presentations.length > 0 && (
            <>
              {/* Sort button and icon */}
              <div className="flex justify-end items-center">
                <button
                  onClick={handleSortToggle}
                  className="flex items-center space-x-1 text-sm text-gray-500 hover:text-blue-600 transition-colors duration-200 rounded-lg py-1 px-2 border border-transparent hover:border-blue-400"
                >
                  <span className="font-medium">
                    {isLatestFirst ? "Latest First" : "Oldest First"}
                  </span>
                  {isLatestFirst ? (
                    <ArrowDownWideNarrowIcon className="h-4 w-4" />
                  ) : (
                    <ArrowUpWideNarrowIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
              <div className="space-y-3 px-4 mt-1">
                {sortedPresentations.map((presentation) => (
                  <PPTCard key={presentation.id} pptData={presentation} />
                ))}
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
      <ResizeButton setRightSidebarWidth={setRightSidebarWidth} />
    </div>
  );
};

export default RightSidebar;
