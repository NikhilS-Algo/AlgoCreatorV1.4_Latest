import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../../store';

export interface DateRangeState {
  from: string;
  to: string;
}

const defaultSelectedStartDate = new Date('2001-01-01T00:00:00.000Z').toISOString();
const defaultSelectedEndDate = new Date().toISOString();

const initialState: DateRangeState = {
  from: defaultSelectedStartDate,
  to: defaultSelectedEndDate,
};

export const selectedDateRangeSlice = createSlice({
  name: 'selectedDateRange',
  initialState,
  reducers: {
    setSelectedDateRange: (state, action: PayloadAction<{ from: string; to: string }>) => {
      state.from = action.payload.from;
      state.to = action.payload.to;
    },
    setSelectedFromDate: (state, action: PayloadAction<string>) => {
      state.from = action.payload;
    },
    setSelectedToDate: (state, action: PayloadAction<string>) => {
      state.to = action.payload;
    },
  },
});

export const { setSelectedDateRange, setSelectedFromDate, setSelectedToDate } = selectedDateRangeSlice.actions;

export const selectSelectedDateRange = (state: RootState) => state.selectedDateRange;

export default selectedDateRangeSlice.reducer;
