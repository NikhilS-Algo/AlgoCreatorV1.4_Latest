import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  username: string | null;
  exp: number | null;
}

export interface LoginPayload {
  token: string;
  username: string;
  exp: number;
}

// Load from localStorage (hydration)
const storedAuth = localStorage.getItem("authState");
const parsedAuth: AuthState | null = storedAuth ? JSON.parse(storedAuth) : null;

const initialState: AuthState = parsedAuth || {
  token: null,
  isAuthenticated: false,
  username: null,
  exp: null,
};

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginSuccess(state, action: PayloadAction<LoginPayload>) {
      state.token = action.payload.token;
      state.username = action.payload.username;
      state.exp = action.payload.exp;
      state.isAuthenticated = true;

      // Save state
      localStorage.setItem("authState", JSON.stringify(state));
    },
    Logout(state) {
      state.token = null;
      state.username = null;
      state.isAuthenticated = false;
      state.exp = null;

      // Clear localStorage
      localStorage.removeItem("authState");
    },
  },
});

export const { loginSuccess, Logout } = authSlice.actions;
export default authSlice.reducer;

export const selectAuth = (state: { auth: AuthState }) => state.auth;
