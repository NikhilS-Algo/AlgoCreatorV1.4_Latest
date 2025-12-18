import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface FoldersLoadingState {
  value: string;
}

const initialState: FoldersLoadingState = {
  value: "loaded",
}

export const foldersLoadingSlice = createSlice({
  name: 'foldersLoading',
  initialState,
  reducers: {
    setFoldersLoading: (state, action: PayloadAction<string>) => {
      state.value = action.payload
    },
  },
})

export const { setFoldersLoading } = foldersLoadingSlice.actions

export default foldersLoadingSlice.reducer

export const selectFoldersLoading = (state: { foldersLoading: FoldersLoadingState }) => state.foldersLoading.value