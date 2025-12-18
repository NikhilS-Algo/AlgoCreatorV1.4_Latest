import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface OpenFeaturesState {
  value: boolean;
}

const initialState: OpenFeaturesState = {
  value: false,
}

export const openFeaturesSlice = createSlice({
  name: 'openFeatures',
  initialState,
  reducers: {
    setOpenFeatures: (state, action: PayloadAction<boolean>) => {
      state.value = action.payload
    },
  },
})

export const { setOpenFeatures } = openFeaturesSlice.actions

export default openFeaturesSlice.reducer

export const selectOpenFeatures = (state: { openFeatures: OpenFeaturesState }) => state.openFeatures.value