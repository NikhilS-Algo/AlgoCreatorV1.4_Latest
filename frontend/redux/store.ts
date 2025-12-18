import { configureStore } from '@reduxjs/toolkit'
import chatReducer from './features/chat/chatSlice';
import filesDateRangeReducer from '@/redux/features/filters/filesDateRangeSlice';
import selectedDateRangeReducer from '@/redux/features/filters/selectedDateRangeSlice';
import foldersLoadingReducer from '@/redux/features/loading/foldersLoadingSlice';
import foldersDataReducer  from '@/redux/features/filters/FetchedFoldersSlice'
import selectedFilesReducer from '@/redux/features/filters/selectedFilesSlice';
import presentationsReducer from '@/redux/features/outputs/presentationsSlice';
import openFeaturesReducer from '@/redux/features/loading/openFeaturesSlice';
import mainTabReducer from '@/redux/features/loading/mainTabSlice';
import sidebarsOpenReducer from '@/redux/features/loading/sidebarsOpenSlice';
import authReducer from './features/auth/authSlice';
import sessionIdReducer from "./features/filters/sessionIdSlice"; 
import generationReducer from "./features/generation/generationSlice"

// Configure the store
export const makeStore = () => {
  return configureStore({
    reducer: {
      chat: chatReducer,
      filesDateRange: filesDateRangeReducer,
      selectedDateRange: selectedDateRangeReducer,
      foldersLoading: foldersLoadingReducer,
      foldersData: foldersDataReducer,
      selectedFiles: selectedFilesReducer,
      presentations: presentationsReducer,
      openFeatures: openFeaturesReducer,
      mainTab: mainTabReducer,
      sidebarsOpen: sidebarsOpenReducer,
      auth: authReducer,
      sessionId: sessionIdReducer,
      generation: generationReducer,
    },
  })
}

// Infer the type of makeStore
export type AppStore = ReturnType<typeof makeStore>
// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
