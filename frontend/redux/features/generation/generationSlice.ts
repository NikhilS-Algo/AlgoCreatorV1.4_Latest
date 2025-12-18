import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface GenerationState {
    isGenerating: boolean;
    generationProgress: number;
    isComplete: boolean;
    sessionId: string | null;
    presentationId: string | null;
    pptxFileUrl: string | null;
    fileName: string;
    loadingPreview: boolean;
    files: File[];
    query: string;
    minSlides: number;
    maxSlides: number;
    style: string;
    content: string;
    template: string;
    outline: string | null;
    currentStep: number;
    dataSourceChoice:string;
}

const initialState: GenerationState = {
    isGenerating: false,
    generationProgress: 0,
    isComplete: false,
    sessionId: null,
    presentationId: null,
    pptxFileUrl: null,
    fileName: "Generated_Presentation.pdf",
    loadingPreview: false,
    files: [],
    query: "",
    minSlides: 5,
    maxSlides: 10,
    style: "professional",
    content: "bullet-points",
    template: "blue",
    outline: "",
    currentStep: 0,
    dataSourceChoice: "",
};

const generationSlice = createSlice({
    name: "generation",
    initialState,
    reducers: {
        startGeneration(state) {
            state.isGenerating = true;
            state.generationProgress = 0;
            state.isComplete = false;
        },
        setProgress(state, action: PayloadAction<number>) {
            state.generationProgress = action.payload;
        },
        setComplete(state, action: PayloadAction<boolean>) {
            state.isComplete = action.payload;
        },
        setSessionId(state, action: PayloadAction<string | null>) {
            state.sessionId = action.payload;
        },
        setPresentationId(state, action: PayloadAction<string | null>) {
            state.presentationId = action.payload;
        },
        setPreviewLoading(state, action: PayloadAction<boolean>) {
            state.loadingPreview = action.payload;
        },
        setPptxFile(state, action: PayloadAction<string | null>) {
            state.pptxFileUrl = action.payload;
        },
        setFileName(state, action: PayloadAction<string>) {
            state.fileName = action.payload;
        },
        setFiles(state, action: PayloadAction<File[]>) {
            state.files = action.payload;
        },
        setQuery(state, action: PayloadAction<string>) {
            state.query = action.payload;
        },
        setSlideRange(state, action: PayloadAction<{ min: number; max: number }>) {
            state.minSlides = action.payload.min;
            state.maxSlides = action.payload.max;
        },
        setStyle(state, action: PayloadAction<string>) {
            state.style = action.payload;
        },
        setContent(state, action: PayloadAction<string>) {
            state.content = action.payload;
        },
        setTemplate(state, action: PayloadAction<string>) {
            state.template = action.payload;
        },
        setOutline(state, action: PayloadAction<string>) {
            state.outline = action.payload;
        },
        setStep(state, action: PayloadAction<number>) {
            state.currentStep = action.payload;
        },
        setDataSourceChoice(state, action: PayloadAction<string>) {
            state.dataSourceChoice = action.payload;
        },
        resetGeneration() {
            return initialState;
        }
    },
});

export const {
    startGeneration,
    setProgress,
    setComplete,
    setSessionId,
    setPresentationId,
    setPreviewLoading,
    setPptxFile,
    setFileName,
    resetGeneration,
    setFiles,
    setQuery,
    setSlideRange,
    setStyle,
    setContent,
    setTemplate,
    setOutline,
    setStep,
    setDataSourceChoice,
} = generationSlice.actions;

export default generationSlice.reducer;
