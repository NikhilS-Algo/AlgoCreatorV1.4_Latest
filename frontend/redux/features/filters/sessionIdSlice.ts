import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface SessionIdState {
  value: string;
}

const initialState: SessionIdState = {
  value: "", // initially no session id
};

export const sessionIdSlice = createSlice({
  name: "sessionId",
  initialState,
  reducers: {
    setSessionId: (state, action: PayloadAction<string>) => {
      state.value = action.payload;
    },
    clearSessionId: (state) => {
      state.value = "";
    },
  },
});

export const { setSessionId, clearSessionId } = sessionIdSlice.actions;

export default sessionIdSlice.reducer;

export const selectSessionId = (state: { sessionId: SessionIdState }) =>
  state.sessionId.value;
