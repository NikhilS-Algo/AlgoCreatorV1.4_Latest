import React, { useEffect, useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Send, Search } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/redux/hooks"; 
import {
  addMessage,
  updateLastMessage,
  ChatMessage,
} from "@/redux/features/chat/chatSlice"; 
import { useToast } from "@/hooks/use-toast";
import { useAxios } from "@/hooks/useAxios";
import { setPresentations, Presentation } from "@/redux/features/outputs/presentationsSlice";
import { selectSessionId, setSessionId } from "@/redux/features/filters/sessionIdSlice";
import { v4 as uuidv4 } from "uuid";

interface SendChatButtonProps {
  message: string;
  setMessage: React.Dispatch<React.SetStateAction<string>>;
}

interface chatResponse {
  reply: string;
  session_id: string;
}

const SendChatButton = ({ message, setMessage }: SendChatButtonProps) => {
  const CHAT_API_URL = process.env.NEXT_PUBLIC_CHAT_API_URL;
  const LIST_PDFS_URL = process.env.NEXT_PUBLIC_LIST_PDFS_API_URL;
  const sessionId = useAppSelector(selectSessionId);

  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const [isBotReplying, setIsBotReplying] = useState(false);

  const {
    data: chatData,
    error: chatError,
    loaded: chatLoaded,
    callAPI: callChatAPI,
    cancel: cancelChat,
  } = useAxios<chatResponse>();

  const {
    data: generatedPPTData,
    error: generatedPPTError,
    loaded: generatedPPTLoaded,
    callAPI: callGeneratedPPTAPI,
    cancel: cancelGeneratedPPTs,
  } = useAxios<Presentation[]>();


  useEffect(() => {
    if (chatLoaded) {
      setIsBotReplying(false);
      if (chatError) {
        // Handle failed API call
        dispatch(
          updateLastMessage({
            text: `Error: ${chatError}`,
            isLoading: false,
            from: "chatbot", 
            isError: true,
          })
        );
        toast({
          variant: "destructive",
          title: "API Error",
          description: "Failed to get a response from the chatbot.",
          duration: 3000,
        });
      } else if (chatData) {
        dispatch(
          updateLastMessage({
            text: chatData.reply,
            isLoading: false,
            from: "chatbot",
          })
        );
        fetchGeneratedPPTs();
      }
    }
  }, [chatData, chatError, chatLoaded, dispatch, toast]);

  useEffect(() => {
    if (generatedPPTLoaded) {
      if (!generatedPPTError && generatedPPTData) {
        dispatch(setPresentations(generatedPPTData));
      }
    }
  }, [generatedPPTLoaded, generatedPPTError, generatedPPTData])

  useEffect(() => {
    fetchGeneratedPPTs();
  }, [])

  const fetchChatResults = async (userMessage: ChatMessage) => {
    let activeSessionId = sessionId;
    if (!activeSessionId) {
      activeSessionId = uuidv4(); // generate new session id
      dispatch(setSessionId(activeSessionId));
    }

    const payload = {
      message: userMessage.text,
      session_id: activeSessionId 
    };
    console.log(payload);
    
    try{
      if (CHAT_API_URL) await callChatAPI(CHAT_API_URL, "POST", payload);
      else {
        setIsBotReplying(false);
        dispatch(
          updateLastMessage({
            text: `Error: API Error`,
            isLoading: false,
            from: "chatbot", 
            isError: true,
          })
        );
        return;
      }
    }
    catch(error) {
    }
  }

  const fetchGeneratedPPTs = async() => {
    if (LIST_PDFS_URL) {
      await callGeneratedPPTAPI(LIST_PDFS_URL, "GET");
    }
  }

  const handleSendMessage = () => {
    // Prevent sending empty messages
    if (!message.trim()) {
      toast({
        variant: "destructive",
        title: "Missing Information",
        description: "Please Enter a Message",
        duration: 3000,
      });
      return;
    }

    setIsBotReplying(true);

    // 1. Create the user's message object
    const userMessage: ChatMessage = {
      from: "user",
      text: message,
      time: new Date().toLocaleString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }),
    };

    // 2. Dispatch the user's message to the Redux store
    dispatch(addMessage(userMessage));
    setMessage(""); // Clear the input field

    // 3. Dispatch a "loading" indicator message from the chatbot
    const loadingMessage: ChatMessage = {
      from: "chatbot",
      text: "•••",
      time: new Date().toLocaleString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }),
      isLoading: true,
    };
    dispatch(addMessage(loadingMessage));

    // 4. Simulate an API call to get the chatbot's response
    fetchChatResults(userMessage);
  };
  return (
      <Button
        size="sm"
        id="send-btn"
        className="bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 transition-all duration-150 shadow-sm"
        onClick={handleSendMessage}
        disabled={isBotReplying}
      >
        <Send className="h-4 w-4" />
      </Button>
  );
};

export default SendChatButton;
