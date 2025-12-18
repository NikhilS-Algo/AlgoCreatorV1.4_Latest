import React from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChevronLeft, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import {
  selectLeftSidebarOpen,
  selectRightSidebarOpen,
  setLeftSidebarOpen,
  setRightSidebarOpen,
} from "@/redux/features/loading/sidebarsOpenSlice";


const HeaderButtons = () => {
  const leftSidebarOpen = useAppSelector(selectLeftSidebarOpen);
  const rightSidebarOpen = useAppSelector(selectRightSidebarOpen);
  const dispatch = useAppDispatch();


  return (
    <div className="flex w-full">
      <div className="flex items-center space-x-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => dispatch(setLeftSidebarOpen(!leftSidebarOpen))}
          className="text-gray-600 hover:bg-gray-100"
        >
          <ChevronLeft
            className={`h-4 w-4 transition-transform ${
              leftSidebarOpen ? "" : "rotate-180"
            }`}
          />
        </Button>
      </div>
      <TabsList className="grid w-full grid-cols-3 bg-gradient-to-r from-blue-50 to-gray-50 m-2 border border-blue-200">
        {["chat", "dashboard", "generate"].map((tab) => (
          <TabsTrigger
            key={tab}
            value={tab}
            id={`${tab}-tab`}
            className="data-[state=active]:bg-white data-[state=active]:text-blue-600 capitalize"
          >
            {tab}
          </TabsTrigger>
        ))}
      </TabsList>
      <div className="flex items-center space-x-2">
        <Button
          variant="ghost"
          size="sm"
          id="outputs-toggle-btn"
          onClick={() => dispatch(setRightSidebarOpen(!rightSidebarOpen))}
          className="text-gray-600 hover:bg-gray-100"
        >
          <ChevronLeft
            className={`h-4 w-4 transition-transform ${
              rightSidebarOpen ? "rotate-180" : ""
            }`}
          />
        </Button>
      </div>
    </div>
  );
};

export default HeaderButtons;
