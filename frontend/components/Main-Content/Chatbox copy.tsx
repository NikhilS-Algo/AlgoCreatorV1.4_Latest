'use client'
import React, { useEffect, useRef, useState } from "react";
import { useAppSelector } from "@/redux/hooks"; 
import { selectChatMessages } from "@/redux/features/chat/chatSlice"; 
import ThreeDotsLoader from "../ui/ThreeDotsLoader";

const Chatbox = () => {
  const chats = useAppSelector(selectChatMessages);

  const lastMessageRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  //-------------------------- for take a few minutes -----------------------------------//
  useEffect(() => {
    scrollToLastMessage();

    // Check if latest message is loading
    const last = chats[chats.length - 1];
    if (last?.from === "chatbot" && last?.isLoading) {
      setShowSlowMessage(false);

      const timer = setTimeout(() => {
        setShowSlowMessage(true);
      }, 10000); // 10 seconds

      return () => clearTimeout(timer);
    } else {
      setShowSlowMessage(false);
    }
  }, [chats]);
//---------------------------------------------
  const [showSlowMessage, setShowSlowMessage] = useState(false);

  const scrollToLastMessage = () => {
    lastMessageRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    setShowScrollButton(false);
  };

  const handleScroll = () => {
    const container = chatContainerRef.current;
    if (container) {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isScrolledUp = scrollHeight - scrollTop > clientHeight + 100;
      setShowScrollButton(isScrolledUp);
    }
  };

  useEffect(() => {
    scrollToLastMessage();
  }, [chats]);

  const formatMessage = (message: string) => {
    const parts = message.split("\n");
    const formattedParts: React.JSX.Element[] = [];

    parts.forEach((part, index) => {
      if (part.trim() === "") {
        formattedParts.push(<br key={`br-${index}`} />);
        return;
      }

      if (part.includes("```json")) {
        const beforeJson = part.split("```json")[0];
        const afterJsonSplit = part.split("```json")[1];
        const jsonContent = afterJsonSplit
          ? afterJsonSplit.split("```")[0]
          : "";
        const afterJson = afterJsonSplit ? afterJsonSplit.split("```")[1] : "";

        if (beforeJson.trim()) {
          formattedParts.push(
            <div key={`before-${index}`} className="mb-2">
              {formatTextWithBold(beforeJson)}
            </div>
          );
        }

        if (jsonContent.trim()) {
          try {
            const parsedJson = JSON.parse(jsonContent.trim());
            formattedParts.push(
              <div key={`json-${index}`} className="mb-4">
                <div className="bg-gray-100 border border-gray-300 rounded-lg p-3 overflow-x-auto">
                  <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                    {JSON.stringify(parsedJson, null, 2)}
                  </pre>
                </div>
              </div>
            );
          } catch (e) {
            formattedParts.push(
              <div key={`code-${index}`} className="mb-4">
                <div className="bg-gray-100 border border-gray-300 rounded-lg p-3 overflow-x-auto">
                  <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                    {jsonContent.trim()}
                  </pre>
                </div>
              </div>
            );
          }
        }

        if (afterJson && afterJson.trim()) {
          formattedParts.push(
            <div key={`after-${index}`} className="mb-2">
              {formatTextWithBold(afterJson)}
            </div>
          );
        }
      } else {
        const processedPart = processInlineJson(part, index);
        formattedParts.push(...processedPart);
      }
    });

    return formattedParts;
  };

  const processInlineJson = (text: string, baseIndex: number) => {
    const parts: React.JSX.Element[] = [];
    let currentText = text;
    let partIndex = 0;

    const jsonPattern = /(\[[\s\S]*?\]|\{[\s\S]*?\})/g;
    let match;
    let lastIndex = 0;

    while ((match = jsonPattern.exec(currentText)) !== null) {
      const beforeJson = currentText.slice(lastIndex, match.index);
      const jsonCandidate = match[1];

      if (beforeJson.trim()) {
        parts.push(
          <div key={`text-${baseIndex}-${partIndex}`} className="mb-2">
            {formatTextWithBold(beforeJson)}
          </div>
        );
        partIndex++;
      }

      try {
        const parsedJson = JSON.parse(jsonCandidate);
        parts.push(
          <div key={`inline-json-${baseIndex}-${partIndex}`} className="mb-4">
            <div className="bg-gray-100 border border-gray-300 rounded-lg p-3 overflow-x-auto">
              <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                {JSON.stringify(parsedJson, null, 2)}
              </pre>
            </div>
          </div>
        );
      } catch (e) {
        parts.push(
          <div key={`text-${baseIndex}-${partIndex}`} className="mb-2">
            {formatTextWithBold(jsonCandidate)}
          </div>
        );
      }

      lastIndex = match.index + match[0].length;
      partIndex++;
    }

    const remainingText = currentText.slice(lastIndex);
    if (remainingText.trim()) {
      parts.push(
        <div key={`text-${baseIndex}-${partIndex}`} className="mb-2">
          {formatTextWithBold(remainingText)}
        </div>
      );
    }

    if (parts.length === 0) {
      parts.push(
        <div key={`text-${baseIndex}`} className="mb-2">
          {formatTextWithBold(text)}
        </div>
      );
    }

    return parts;
  };

  const formatTextWithBold = (text: string) => {
    const boldRegex = /\*\*(.*?)\*\*/g;
    const parts = text.split(boldRegex);

    return parts.map((part, index) => {
      if (index % 2 === 1) {
        return (
          <strong key={`bold-${index}`} className="font-semibold">
            {part}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div className="relative h-full">
      <div
        ref={chatContainerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto"
      >
        <div className="w-full max-w-[1000px] mx-auto space-y-4">
          {chats &&
            chats.map((chat, index) => {
              const isLastMessage = chats.length - 1 === index;
              return chat.from === "chatbot" ? (
                <div
                  ref={isLastMessage ? lastMessageRef : null}
                  className="flex items-start space-x-3 max-w-[90%] justify-start px-4"
                  key={index}
                >
                  <div className="inline-flex flex-col">
                    {/* MESSAGE BUBBLE */}
                    <div
                      className={`relative rounded-lg p-4 pb-10 border ${chat.isError
                          ? "bg-red-50 border-red-200/50"
                          : "bg-white border-gray-200"
                        }`}
                    >
                      {/* MESSAGE CONTENT */}
                      <div
                        className={`text-sm ${chat.isError ? "text-red-700" : "text-gray-800"
                          } leading-relaxed`}
                      >
                        {chat.isLoading ? (
                          showSlowMessage ? (
                            <div className="flex items-center gap-2">
                              <ThreeDotsLoader />
                              <span className="text-sm text-blue-600 italic">
                                This may take a few minutes…
                              </span>
                            </div>
                          ) : (
                            <ThreeDotsLoader />
                          )
                        ) : (
                          formatMessage(chat.text)
                        )}
                      </div>

                      {/* EDIT BUTTON IN RIGHT-BOTTOM */}
                      {!chat.isLoading && index === chats.length - 1 && (
                        <div className="absolute bottom-2 right-2 group">
                          <button
                          //   className="
                          //   text-xs text-blue-600 
                          //   bg-blue-50 
                          //   px-3 py-1 
                          //   rounded-md 
                          //   border border-blue-200 
                          //   hover:bg-blue-100 
                          //   transition shadow-sm
                          // "
                            className="
                            text-xs text-blue-600
                            bg-blue-50 
                            px-3 py-1 
                            rounded-md 
                            border border-blue-200
                            transition-all duration-200
                            hover:bg-blue-100 
                            hover:text-blue-700
                            hover:shadow-md 
                            hover:scale-[1.02]
                          "
                          >
                            Edit
                          </button>

                          {/* Tooltip */}
                          <div
                            className="
                            absolute bottom-full right-0 mb-1 
                            bg-black text-white 
                            text-[10px] px-2 py-1 
                            rounded 
                            opacity-0 group-hover:opacity-100 
                            transition 
                            pointer-events-none
                            whitespace-nowrap
                          "
                          >
                            Coming soon
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-blue-600 mt-2 font-medium">
                      {chat.time}
                      {/* EDIT TEXT (Only for latest chatbot response)
                      {!chat.isLoading && index === chats.length - 1 && (
                        <div className="mt-1 relative group w-fit">
                          <span className="text-blue-600 text-xs font-medium cursor-pointer hover:underline">
                            Edit
                          </span> */}

                          {/* Tooltip */}
                          {/* <div className="
                            absolute left-1/2 -translate-x-1/2 top-full mt-1
                            bg-black text-white text-[10px] 
                            px-2 py-1 rounded-md 
                            opacity-0 group-hover:opacity-100 
                            whitespace-nowrap transition
                            pointer-events-none
                            z-20
                            ">
                            Coming soon
                          </div>
                        </div>
                      )} */}
                    </div>
                  </div>
                </div>
              ) : (
                  <div
                  ref={isLastMessage ? lastMessageRef : null}
                  className="flex items-start space-x-3 max-w-[90%] ml-auto justify-end px-4"
                  key={index}
                >
                  <div className="inline-flex flex-col">
                    <div className="bg-gradient-to-r from-blue-50 to-gray-50 rounded-tl-xl rounded-bl-xl rounded-br-xl p-4 border border-blue-200/50">
                      <div className="text-sm text-gray-700 leading-relaxed">
                        {chat.text}
                      </div>
                    </div>
                    <div className="flex justify-end text-xs text-blue-600 mt-2 font-medium">
                      {chat.time}
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
      {showScrollButton && (
        <button
          onClick={scrollToLastMessage}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-blue-400 hover:bg-blue-500 text-white rounded-full h-12 w-12 flex items-center justify-center shadow-lg transition-opacity duration-300"
          aria-label="Scroll to bottom"
        >
          <svg
            xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      )}
    </div>
  );
};

export default Chatbox;
