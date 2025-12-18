import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface Presentation {
  id: number;
  file_name: string;
  file_type: string;
  file_path: string;
  file_size: string;
  creation_date: string;
}

interface PresentationState {
  presentations: Presentation[];
}

const initialState: PresentationState = {
  presentations: [],
};

export const presentationsSlice = createSlice({
  name: "presentations",
  initialState,
  reducers: {
    addPresentation: (state, action: PayloadAction<Presentation>) => {
      state.presentations.push(action.payload);
    },
    removePresentation: (state, action: PayloadAction<number>) => {
      state.presentations = state.presentations.filter(
        (presentation) => presentation.id !== action.payload
      );
    },
    setPresentations: (state, action: PayloadAction<Presentation[]>) => {
      state.presentations = action.payload;
    },
  },
});

export const { addPresentation, removePresentation, setPresentations } =
  presentationsSlice.actions;

export default presentationsSlice.reducer;

export const selectPresentations = (state: {
  presentations: PresentationState;
}) => state.presentations.presentations;
