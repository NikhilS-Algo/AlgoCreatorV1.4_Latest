import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface MainTabState {
  value: string;
}

const initialState: MainTabState = {
  value: "chat",
}

export const mainTabSlice = createSlice({
  name: 'mainTab',
  initialState,
  reducers: {
    setMainTab: (state, action: PayloadAction<string>) => {
      state.value = action.payload
    },
  },
})

export const { setMainTab } = mainTabSlice.actions

export default mainTabSlice.reducer

export const selectMainTab = (state: { mainTab: MainTabState }) => state.mainTab.value