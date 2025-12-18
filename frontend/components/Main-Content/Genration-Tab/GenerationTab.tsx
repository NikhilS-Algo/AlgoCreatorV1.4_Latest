"use client"

import { useState } from "react"
import { PresentationForm } from "./presentation-form"
import { GenerationPanel } from "./generation-panel"
import { getPresentation } from "@/lib/api"
import { selectAuth } from "@/redux/features/auth/authSlice"
import { useDispatch, useSelector } from "react-redux";
import {
  startGeneration,
  setProgress,
  setComplete,
  setSessionId,
  setPresentationId,
  resetGeneration
} from "@/redux/features/generation/generationSlice";
import { RootState } from "@/redux/store";


export default function GenerateTab() {
  const dispatch = useDispatch();
  const [localFiles, setLocalFiles] = useState<File[]>([]);
  const {
    isGenerating,
    generationProgress,
    isComplete,
    sessionId,
    presentationId
  } = useSelector((state: RootState) => state.generation);

  const { username } = useSelector(selectAuth)

  const handleGenerate = async (formData: {
    query: string;
    files: File[];
    minSlides: number;
    maxSlides: number;
    style: string;
    content: string;
    template: string;
    sessionId: string;
    dataSourceChoice: string
    presentationId: string | null
  }) => {
    console.log("[Frontend] Starting presentation generation:", formData);
    dispatch(startGeneration());


    try {
      if (!formData.presentationId) {
        throw new Error("Missing presentation ID from template generation");
      }

      const response = await getPresentation(formData.presentationId, username || "guest_user");
      console.log("✅ Backend presentation fetched:", response);
      dispatch(setPresentationId(formData.presentationId));
      dispatch(setSessionId(formData.sessionId));
      dispatch(setProgress(100));
      dispatch(setComplete(true));
    } catch (err: any) {
      console.error("❌ Presentation generation failed:", err);
      alert(`Error generating presentation: ${err.message}`);
    }
  };


  const handleClosePanel = () => {
    // ✅ User explicitly closes it → Reset everything
    dispatch(resetGeneration());
    setLocalFiles([]); 
  };


  return (
    <main className="min-h-screen bg-backgroun p-8 md:p-12">
      {/* Commented out split-view for future use - currently using full-width form with overlay generation panel */}
      {/* <div className="flex min-h-screen">
        <div className={`flex-1 overflow-y-auto transition-all duration-300 ${isGenerating ? "w-1/2" : "w-full"}`}>
          <PresentationForm onGenerate={handleGenerate} isLoading={isGenerating} />
        </div>
        {isGenerating && (
          <div className="w-1/2 border-l border-input bg-card animate-slide-in overflow-hidden">
            <GenerationPanel
              isOpen={isGenerating}
              progress={generationProgress}
              onClose={handleClosePanel}
              isComplete={isComplete}
              pptxFileUrl={pptxFileUrl}
            />
          </div>
        )}
      </div> */}

      <div className="min-h-screen flex items-stretch">
        {/* Left side: Form always visible and editable */}
        <div className={`transition-all duration-300 ${isGenerating ? "w-1/2" : "w-full"} overflow-auto `}>
          <PresentationForm
            onGenerate={handleGenerate}
            isLoading={isGenerating}
            localFiles={localFiles}
            setLocalFiles={setLocalFiles}
          />
        </div>

        {/* Right side: Generation panel slides in when generating */}
        {isGenerating && (
          <div
            className="w-1/2 border-l border-input bg-card animate-slide-in sticky top-0 h-screen overflow-hidden">
              <GenerationPanel
              isOpen={isGenerating || isComplete}
              progress={generationProgress}
              onClose={handleClosePanel}
              isComplete={isComplete}
              sessionId={sessionId || undefined}
              presentationId={presentationId}
            />

          </div>
        )}
      </div>
    </main>
  )
}
