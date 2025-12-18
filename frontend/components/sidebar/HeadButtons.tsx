import React from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MessageSquare, History } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeadButtonsProps {
  leftSidebarTab: string;
  setLeftSidebarTab: React.Dispatch<React.SetStateAction<string>>;
}

const HeadButtons = ({
  leftSidebarTab,
  setLeftSidebarTab,
}: HeadButtonsProps) => {
  return (
    <div className="px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Tabs
          value={leftSidebarTab}
          onValueChange={setLeftSidebarTab}
          className="flex-1 min-w-[152px]"
        >
          <TabsList className="grid w-full grid-cols-2 bg-white border border-blue-500">
            <TabsTrigger
              value="filters"
              className="flex items-center data-[state=active]:bg-blue-500 data-[state=active]:text-white border-0"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Filters
            </TabsTrigger>
            <TabsTrigger
              value="history"
              className="flex items-center data-[state=active]:bg-blue-500 data-[state=active]:text-white border-0"
            >
              <History className="h-4 w-4 mr-2" />
              History
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {/* <Button
          variant="outline"
          size="sm"
          className="flex items-center px-3 py-2 text-sm font-medium bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 hover:text-white transition-all duration-200 shadow-sm"
          onClick={() => {
            console.log("New chat created");
          }}
        >
          <span className="text-lg mr-1">+</span>
          New Chat
        </Button> */}
      </div>
    </div>
  );
};

export default HeadButtons;
