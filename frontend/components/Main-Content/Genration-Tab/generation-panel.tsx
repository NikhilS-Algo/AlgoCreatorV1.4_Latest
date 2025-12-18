"use client"

import { useState, useEffect } from "react"
import { X, Share2 } from "lucide-react"
import { PptxViewer } from "./pptx-viewer"
import { getPresentation } from "@/lib/api" // ✅ use same API helper
import { selectAuth } from "@/redux/features/auth/authSlice"
import { useDispatch, useSelector } from "react-redux";
import {
  setPptxFile,
  setFileName,
  setPreviewLoading
} from "@/redux/features/generation/generationSlice";
import { RootState } from "@/redux/store";


interface GenerationPanelProps {
  isOpen: boolean
  progress: number
  onClose: () => void
  isComplete: boolean
  sessionId?: string
  presentationId: string | null
}

export function GenerationPanel({
  isOpen,
  progress,
  onClose,
  isComplete,
  sessionId,
  presentationId
}: GenerationPanelProps) {
  const [isClosing, setIsClosing] = useState(false)
  const {
    pptxFileUrl,
    fileName,
    loadingPreview
  } = useSelector((state: RootState) => state.generation);

  const dispatch = useDispatch();

  const [error, setError] = useState<string | null>(null)

  const { username } = useSelector(selectAuth)

  const handleClose = () => {
    setIsClosing(true)
    setTimeout(() => {
      setIsClosing(false)
      onClose()
    }, 300)
  }

  // 🧠 Fetch generated presentation from backend once generation is complete
  useEffect(() => {
    if (isComplete && presentationId) {
      const fetchPresentation = async () => {
        dispatch(setPreviewLoading(true));
        setError(null)
        try {
          console.log("📡 Fetching presentation preview for ID:", presentationId)
          const response = await getPresentation(
            presentationId,
            username || "guest_user"
          )

          // ✅ Convert blob to downloadable & viewable URL
          const blob = new Blob([response.data], { type: response.data.type || "application/vnd.openxmlformats-officedocument.presentationml.presentation" })
          const url = URL.createObjectURL(blob)
          dispatch(setPptxFile(url));


          // Extract filename if sent in headers
          const disposition = response.headers["content-disposition"]
          if (disposition && disposition.includes("filename=")) {
            const match = disposition.match(/filename="?([^"]+)"?/)
            if (match && match[1]) dispatch(setFileName(match[1]));
          }

          console.log("Presentation ready for preview:", url)
        } catch (err: any) {
          console.error("Failed to fetch presentation:", err)
          setError(err.message)
        } finally {
          dispatch(setPreviewLoading(false));
        }
      }

      fetchPresentation()
    }
  }, [isComplete, presentationId, username])

  // PDF download 
  const handleDownload = () => {
    if (pptxFileUrl) {
      const link = document.createElement("a")
      link.href = pptxFileUrl
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }

  return (
    <div className="h-screen w-full bg-card shadow-2xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-6 flex-shrink-0">
        <h3 className="text-lg font-semibold text-foreground">
          {isComplete ? "Presentation Preview" : "Generating Presentation"}
        </h3>
        <button
          onClick={handleClose}
          className="text-muted-foreground hover:text-foreground p-1 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!isComplete ? (
          // 🌀 Generation progress
          <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-6">
            <div className="relative w-24 h-24 animate-scale-in">
              <div className="absolute inset-0 rounded-full border-4 border-input" />
              <div
                className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary border-r-primary animate-spin"
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-2xl font-bold text-foreground">
                  {Math.round(progress)}%
                </p>
              </div>
            </div>
            <p className="text-sm font-medium text-foreground">
              {progress < 30
                ? "Analyzing content..."
                : progress < 60
                  ? "Designing slides..."
                  : progress < 90
                    ? "Adding visuals..."
                    : "Finalizing..."}
            </p>
            <div className="w-full max-w-xs bg-input rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-primary to-accent h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : (
          // ✅ Presentation preview
          <div className="flex-1 flex flex-col p-4 gap-4 overflow-hidden">
            {loadingPreview ? (
              <div className="flex-1 flex items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  Loading presentation preview...
                </p>
              </div>
            ) : error ? (
              <div className="flex-1 flex items-center justify-center text-red-500">
                Failed to load preview: {error}
              </div>
            ) : (
              <div className="flex-1 overflow-hidden">
                <PptxViewer
                  fileUrl={pptxFileUrl || ""}
                  fileName={fileName}
                  onDownload={handleDownload}
                  presentationId={presentationId}
                />
              </div>
            )}

            {/* Footer */}
            <div className="flex gap-2 flex-shrink-0">
              {/* <button className="flex-1 flex items-center justify-center gap-2 bg-secondary hover:bg-secondary/80 text-foreground font-medium py-2.5 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95">
                <Share2 className="w-4 h-4" />
                Share with Team
              </button> */}
              <button
                onClick={handleClose}
                className="flex-1 text-foreground font-medium py-2.5 rounded-lg transition-all duration-200 hover:bg-secondary/50"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
