import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../../store';

// Define the type for a single chat message
export interface ChatMessage {
  from: "user" | "chatbot";
  text: string;
  time: string;
  isLoading?: boolean;
  isError?: boolean;
}

// Define the type for the chat slice's state
export interface ChatState {
  messages: ChatMessage[];
}

// Define the initial state with the welcome message
const initialState: ChatState = {
  messages: [
    {
      from: "chatbot",
      text: "Welcome to AlgoCreator! I'm here to help you generate presentations. How can I assist you today?",
      time: new Date().toLocaleString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }),
      isLoading: false,
      isError: false,
    },
  ],
};

export const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },
    updateLastMessage: (state, action: PayloadAction<Partial<ChatMessage>>) => {
      const lastIndex = state.messages.length - 1;
      if (lastIndex >= 0 && state.messages[lastIndex].from === 'chatbot') {
        state.messages[lastIndex] = { ...state.messages[lastIndex], ...action.payload };
      }
    },
  },
});

export const { addMessage, updateLastMessage } = chatSlice.actions;

export const selectChatMessages = (state: RootState) => state.chat.messages;

export default chatSlice.reducer;
