import React, { useRef, useState, useEffect } from "react";
import { Tabs } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import HeaderButtons from "./HeaderButtons";
import MessageInput from "./MessageInput";
import Chatbox from "@/components/Main-Content/Chatbox";
import VisualizationDashboard from "../visualization dashboard/VisualizationDashboard";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import { selectMainTab, setMainTab } from "@/redux/features/loading/mainTabSlice";
import GenerateTab from "./Genration-Tab/GenerationTab";
import { setLeftSidebarOpen, setRightSidebarOpen } from "@/redux/features/loading/sidebarsOpenSlice";

const MainContent = () => {
  const mainContentRef = useRef<HTMLDivElement>(null);
  const [mainContentWidth, setMainContentWidth] = useState(800);
  const mainTab = useAppSelector(selectMainTab);
  const dispatch = useAppDispatch();
  
  useEffect(() => {
    const element = mainContentRef.current;
    if (!element) return;

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0]) {
        setMainContentWidth(entries[0].contentRect.width);
      }
    });

    resizeObserver.observe(element);
    return () => resizeObserver.disconnect();
  }, []);

  return (
    <div
      ref={mainContentRef}
      className="flex-1 flex flex-col main_content_area"
    >
      <div className="flex-1 flex flex-col overflow-hidden h-full">
        <div className="flex-1 flex flex-col px-4 h-full">

          {/* Tabs (only header controls tab selection, content is always mounted) */}
          <Tabs
            value={mainTab}
            onValueChange={(value) => {
              dispatch(setMainTab(value));
              if (value === "generate") {
                //Close sidebars only when entering the generate tab
                dispatch(setLeftSidebarOpen(false));
                dispatch(setRightSidebarOpen(false));
              } else {
                //Reopen sidebars when switching to chat or dashboard
                dispatch(setLeftSidebarOpen(true));
                dispatch(setRightSidebarOpen(true));
              }
            }}
            className="flex-1 flex flex-col overflow-hidden h-full"
          >
            <HeaderButtons />

            {/* ---------------- CHAT TAB (Always Mounted) ---------------- */}
            <div
              className={`${
                mainTab === "chat" ? "block" : "hidden"
              } flex-1 flex flex-col overflow-hidden h-full`}
            >
              <Card className="flex-1 flex flex-col overflow-hidden">
                <CardContent className="flex-1 p-4 overflow-y-auto h-full">
                  <Chatbox />
                </CardContent>
                <MessageInput />
              </Card>
            </div>

            {/* ---------------- DASHBOARD TAB (Always Mounted) ---------------- */}
            <div
              id="folder-structure-chart"
              className={`${
                mainTab === "dashboard" ? "block" : "hidden"
              } overflow-auto`}
            >
              <VisualizationDashboard parentWidth={mainContentWidth} />
            </div>

            {/* ---------------- GENERATE TAB (Always Mounted) ---------------- */}
            <div
              id="generation-tab"
              className={`${
                mainTab === "generate" ? "block" : "hidden"
              } overflow-auto`}
            >
              <GenerateTab />
            </div>

          </Tabs>
        </div>
      </div>
    </div>
  );
};

export default MainContent;
