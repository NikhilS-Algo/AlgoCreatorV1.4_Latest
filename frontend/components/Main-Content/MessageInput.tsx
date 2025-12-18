import React, { useState, useRef } from "react";
import { Paperclip } from "lucide-react";
import SendChatButton from "./SendChatButton";
import FeatureSelection from "./FeatureSelection";
import RetrieveButton from "./RetrieveButton";

const MessageInput = () => {
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      console.log("Selected file:", file);
    }
  };

  return (
    <div className="px-4 py-3 bg-white justify-center flex">
      <div
        id="chat-input"
        className="flex items-end rounded-xl border border-gray-300 bg-gray-50 px-3 py-2 shadow-sm w-full max-w-[1000px]"
      >
        {/* Input Area */}
        <div className="flex flex-col flex-1 gap-1">
          <textarea
            rows={2}
            placeholder="Type your message or ask to create presentations..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                document.getElementById("send-btn")?.click();
              }
            }}
            className="w-full resize-none bg-transparent border-none focus:ring-0 focus:outline-none text-sm text-gray-800 placeholder:text-gray-400 overflow-y-auto max-h-32"
          />

          {/* Feature Options Inside the Same Box */}
          <div className="mt-1 flex space-x-4 text-xs text-gray-500">
            <FeatureSelection />
            <div className="relative group inline-block">
              {/* <button
                onClick={handleClick}
                className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition bg-gray-200"
                aria-label="Attach file"
              >
                <Paperclip className="w-5 h-5 text-gray-700 dark:text-white" />
              </button> */}

              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/4 px-2 py-1 rounded text-sm text-white bg-black opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                Supported: Text, Images, Presentations, PDF files
              </div>

              {/* Hidden file input */}
              {/* <input
                type="file"
                accept=".pdf,.png,.jpeg,.jpg"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
              /> */}
            </div>
          </div>
        </div>

        {/* Buttons on the Right */}
        <div className="flex gap-2 pl-2">
          <SendChatButton message={message} setMessage={setMessage} />
          {/* <RetrieveButton /> */}
        </div>
      </div>
    </div>
  );
};

export default MessageInput;
