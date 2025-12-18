import React, { useState } from "react";
import { Trash2, MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";

const ChatHistory = () => {
  const chatHistory = [
    {
      id: 1,
      title: "Financial Analysis Q1 2024",
      time: "2 hours ago",
      active: false,
    },
    {
      id: 2,
      title: "Market Trends Presentation",
      time: "1 day ago",
      active: true,
    },
    { id: 3, title: "Revenue Forecasting", time: "3 days ago", active: false },
    {
      id: 4,
      title: "Customer Segmentation",
      time: "1 week ago",
      active: false,
    },
  ];
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-gray-800">Chat History</h3>
        <Button
          variant="ghost"
          size="sm"
          className="text-red-500 hover:bg-red-50"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {chatHistory.map((chat) => (
        <div
          key={chat.id}
          className={`p-3 rounded-lg cursor-pointer transition-all duration-200 ${
            chat.active
              ? "bg-gradient-to-r from-blue-50 via-violet-50 to-purple-50 border border-blue-200 shadow-sm"
              : "hover:bg-gray-50"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-gray-900 truncate">
                {chat.title}
              </h4>
              <p className="text-xs text-blue-600 mt-1">{chat.time}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="opacity-0 group-hover:opacity-100"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ChatHistory;
