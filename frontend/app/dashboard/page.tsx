"use client";
import React, { useState } from "react";
import Navbar from "@/components/navbar/Navbar";
import Sidebar from "@/components/sidebar/Sidebar";
import MainContent from "@/components/Main-Content/MainContent";
import RightSidebar from "@/components/Right Sidebar/RightSidebar";
import { useAppSelector } from "@/redux/hooks";
import { selectRightSidebarOpen } from "@/redux/features/loading/sidebarsOpenSlice";


const page = () => {
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(400);
  const [rightSidebarWidth, setRightSidebarWidth] = useState(300);
  const rightSidebarOpen = useAppSelector(selectRightSidebarOpen);


  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50/20">
      <Navbar />
      <div className="flex flex-1 bg-gradient-to-br from-gray-50 via-white to-blue-50/20 overflow-hidden">
        <Sidebar
          setLeftSidebarWidth={setLeftSidebarWidth}
          leftSidebarWidth={leftSidebarWidth}
        />
        <MainContent />
        {rightSidebarOpen && (
          <RightSidebar
            rightSidebarOpen={rightSidebarOpen}
            rightSidebarWidth={rightSidebarWidth}
            setRightSidebarWidth={setRightSidebarWidth}
          />
        )}
      </div>
    </div>
  );
};

export default page;
