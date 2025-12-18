import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../../store';

export interface DateRangeState {
  from: string;
  to: string;
}

const defaultStartDate = new Date('2001-01-01T00:00:00.000Z').toISOString();
const defaultEndDate = new Date().toISOString();

const initialState: DateRangeState = {
  from: defaultStartDate,
  to: defaultEndDate,
};

export const filesDateRangeSlice = createSlice({
  name: 'filesDateRange',
  initialState,
  reducers: {
    setFilesDateRange: (state, action: PayloadAction<{ from: string; to: string }>) => {
      state.from = action.payload.from;
      state.to = action.payload.to;
    },
    setFromFileDate: (state, action: PayloadAction<string>) => {
      state.from = action.payload;
    },
    setToFileDate: (state, action: PayloadAction<string>) => {
      state.to = action.payload;
    },
  },
});

export const { setFilesDateRange, setFromFileDate, setToFileDate } = filesDateRangeSlice.actions;

export const selectFilesDateRange = (state: RootState) => state.filesDateRange;

export default filesDateRangeSlice.reducer;
