import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../../store'; 

export type SelectedFilesState = number[];

const initialState: SelectedFilesState = [];

export const selectedFilesSlice = createSlice({
  name: 'selectedFiles',
  initialState,
  reducers: {
    appendFile: (state, action: PayloadAction<number>) => {
      if (!state.includes(action.payload)) {
        state.push(action.payload);
      }
    },
    removeFile: (state, action: PayloadAction<number>) => {
      return state.filter(id => id !== action.payload);
    },
    appendFiles: (state, action: PayloadAction<number[]>) => {
      action.payload.forEach(fileId => {
        if (!state.includes(fileId)) {
          state.push(fileId);
        }
      });
    },
    removeFiles: (state, action: PayloadAction<number[]>) => {
      const idsToRemove = new Set(action.payload);
      return state.filter(id => !idsToRemove.has(id));
    },
    clearSelection: (state) => {
      return [];
    },
  },
});

export const { appendFile, removeFile, appendFiles, removeFiles, clearSelection } = selectedFilesSlice.actions;

export const selectSelectedFiles = (state: RootState) => state.selectedFiles;

export default selectedFilesSlice.reducer;
