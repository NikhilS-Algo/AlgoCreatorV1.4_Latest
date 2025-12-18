import React, { useState } from "react";
import ResizeButton from "./ResizeButton";
import HeadButtons from "./HeadButtons";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import ChatHistory from "./ChatHistory";
import DateFilter from "./DateFilter";
import FolderFilter from "./FolderFilter";
import { useAppSelector } from "@/redux/hooks";
import { selectLeftSidebarOpen } from "@/redux/features/loading/sidebarsOpenSlice";

interface SidebarProps {
  leftSidebarWidth: number;
  setLeftSidebarWidth: React.Dispatch<React.SetStateAction<number>>;
}

const Sidebar = ({
  leftSidebarWidth,
  setLeftSidebarWidth,
}: SidebarProps) => {
  const [leftSidebarTab, setLeftSidebarTab] = useState("filters");
  const leftSidebarOpen = useAppSelector(selectLeftSidebarOpen);

  return (
    <div
      className={`${
        leftSidebarOpen ? "flex" : "hidden"
      } bg-blue-50 border-r border-gray-200 flex-col relative shadow-sm`}
      style={{ width: leftSidebarWidth }}
    >
      <HeadButtons
        leftSidebarTab={leftSidebarTab}
        setLeftSidebarTab={setLeftSidebarTab}
      />
      <div className="flex-1 overflow-hidden">
        <Tabs value={leftSidebarTab} className="h-full flex flex-col">
          <TabsContent
            value="filters"
            className="flex-1 overflow-y-auto p-4 space-y-6 m-0"
          >
            <div>
              <h3 className="text-lg font-bold text-gray-800 mb-4">
                Data Selection
              </h3>
              <DateFilter />
              <FolderFilter />
            </div>
          </TabsContent>
          <TabsContent
            value="history"
            className="flex-1 overflow-y-auto p-4 m-0"
          >
            <ChatHistory />
          </TabsContent>
        </Tabs>
      </div>
      <ResizeButton setLeftSidebarWidth={setLeftSidebarWidth} />
    </div>
  );
};

export default Sidebar;
