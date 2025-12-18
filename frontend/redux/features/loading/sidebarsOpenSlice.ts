import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface SidebarsOpenState {
  leftSidebarOpen: boolean;
  rightSidebarOpen: boolean;
}

const initialState: SidebarsOpenState = {
  leftSidebarOpen: true,
  rightSidebarOpen: true,
}

export const sidebarsOpenSlice = createSlice({
  name: 'sidebarsOpen',
  initialState,
  reducers: {
    setLeftSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.leftSidebarOpen = action.payload
    },
    setRightSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.rightSidebarOpen = action.payload
    },
  },
})

export const { setLeftSidebarOpen, setRightSidebarOpen } = sidebarsOpenSlice.actions

export default sidebarsOpenSlice.reducer

export const selectLeftSidebarOpen = (state: { sidebarsOpen: SidebarsOpenState }) => state.sidebarsOpen.leftSidebarOpen
export const selectRightSidebarOpen = (state: { sidebarsOpen: SidebarsOpenState }) => state.sidebarsOpen.rightSidebarOpen