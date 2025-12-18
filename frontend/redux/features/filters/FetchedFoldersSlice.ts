import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// Define the interfaces for the file and folder nodes.
export interface FileNode {
  name: string;
  file_id: number;
  num_slides: number;
  tags: string[];
}

export interface ApiFolderNode {
  name: string;
  description: string;
  subfolders: ApiFolderNode[];
  files: FileNode[];
}

// Define the interface for the entire state.
export interface FoldersData {
  root_node: ApiFolderNode;
  // first_level_folders: string[];
}

// Set the initial state to a complete, empty object.
const initialState: FoldersData = {
  root_node: {
    name: "",
    description: "",
    subfolders: [],
    files: [],
  },
  // first_level_folders: [],
};

export const foldersDataSlice = createSlice({
  name: 'foldersData',
  initialState,
  reducers: {
    setFoldersData: (state, action: PayloadAction<FoldersData>) => {
      return action.payload;
    },
  },
});

export const { setFoldersData } = foldersDataSlice.actions;

export default foldersDataSlice.reducer;

export const selectFoldersData = (state: { foldersData: FoldersData }) => state.foldersData;
