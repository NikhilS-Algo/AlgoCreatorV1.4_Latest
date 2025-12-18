"use client"

import { Download, Loader2, ChevronLeft, ChevronRight, Maximize2, Minimize2 } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { getPPTXPresentation } from "@/lib/api"
import { useSelector, UseSelector } from "react-redux"
import { selectAuth } from "@/redux/features/auth/authSlice"
interface PptxViewerProps {
  fileUrl?: string
  fileName?: string
  onDownload?: () => void
  presentationId: string
}



export function PptxViewer({ fileUrl, fileName = "presentation.pdf", onDownload, presentationId }: PptxViewerProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [pdfDoc, setPdfDoc] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [scale, setScale] = useState(1.5)
  const [pdfLibLoaded, setPdfLibLoaded] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { username } = useSelector(selectAuth);

  // Load PDF.js library
  useEffect(() => {
    const loadPdfJs = async () => {
      try {
        if ((window as any).pdfjsLib) {
          setPdfLibLoaded(true)
          return
        }

        const script = document.createElement('script')
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js'
        script.async = true

        script.onload = () => {
          (window as any).pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'
          setPdfLibLoaded(true)
          console.log("✅ PDF.js loaded successfully")
        }

        script.onerror = () => {
          setError("Failed to load PDF viewer library")
          setIsLoading(false)
        }

        document.body.appendChild(script)
      } catch (err) {
        console.error("Error loading PDF.js:", err)
        setError("Failed to initialize PDF viewer")
        setIsLoading(false)
      }
    }

    loadPdfJs()
  }, [])

  // Load PDF from URL when library is ready
  useEffect(() => {
    if (fileUrl && pdfLibLoaded) {
      console.log("📄 Loading PDF from URL:", fileUrl)
      loadPdf(fileUrl)
    }
  }, [fileUrl, pdfLibLoaded])

  const loadPdf = async (url: string) => {
    try {
      setIsLoading(true)
      setError(null)

      console.log("🔄 Fetching PDF...")

      // Fetch the blob URL
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const blob = await response.blob()
      const arrayBuffer = await blob.arrayBuffer()

      console.log("📦 PDF data loaded, size:", arrayBuffer.byteLength, "bytes")

      const loadingTask = (window as any).pdfjsLib.getDocument({ data: arrayBuffer })
      const pdf = await loadingTask.promise

      console.log("✅ PDF loaded successfully, pages:", pdf.numPages)

      setPdfDoc(pdf)
      setTotalPages(pdf.numPages)
      setCurrentPage(1)
    } catch (err: any) {
      console.error("❌ Error loading PDF:", err)
      setError(err.message || "Failed to load PDF")
      setIsLoading(false)
    }
  }

  // Render current page
  const renderPage = async (pageNum: number) => {
    if (!pdfDoc || !canvasRef.current) return

    try {
      setIsLoading(true)
      console.log("🎨 Rendering page", pageNum)

      const page = await pdfDoc.getPage(pageNum)
      const canvas = canvasRef.current
      const context = canvas.getContext('2d')

      if (!context) {
        throw new Error("Could not get canvas context")
      }

      const viewport = page.getViewport({ scale })
      canvas.height = viewport.height
      canvas.width = viewport.width

      const renderContext = {
        canvasContext: context,
        viewport: viewport
      }

      await page.render(renderContext).promise
      console.log("✅ Page rendered successfully")
      setIsLoading(false)
    } catch (err: any) {
      console.error("❌ Error rendering page:", err)
      setError("Failed to render page")
      setIsLoading(false)
    }
  }

  // Render page when it changes
  useEffect(() => {
    if (pdfDoc && currentPage) {
      renderPage(currentPage)
    }
  }, [pdfDoc, currentPage, scale])

  const nextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(prev => prev + 1)
    }
  }

  const prevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(prev => prev - 1)
    }
  }

  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.key === "ArrowRight" || e.key === " ") {
      e.preventDefault()
      nextPage()
    }
    if (e.key === "ArrowLeft") {
      e.preventDefault()
      prevPage()
    }
    if (e.key === "f" || e.key === "F") {
      toggleFullscreen()
    }
    if (e.key === "+" || e.key === "=") {
      e.preventDefault()
      setScale(prev => Math.min(prev + 0.1, 3))
    }
    if (e.key === "-" || e.key === "_") {
      e.preventDefault()
      setScale(prev => Math.max(prev - 0.1, 0.5))
    }
  }

  useEffect(() => {
    window.addEventListener("keydown", handleKeyPress)
    return () => window.removeEventListener("keydown", handleKeyPress)
  }, [currentPage, totalPages])

  const toggleFullscreen = () => {
    if (!isFullscreen && containerRef.current) {
      containerRef.current.requestFullscreen?.()
    } else if (document.fullscreenElement) {
      document.exitFullscreen?.()
    }
    setIsFullscreen(!isFullscreen)
  }

  const handlePPTXDownload = async () => {
    try {
      const url = await getPPTXPresentation(presentationId, username);

      const link = document.createElement("a");
      link.href = url;
      link.download = "Genrated_Presentation.pptx"; // required for browser; name doesn't matter
      link.click();

      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("PPTX download failed", error);
    }
  };


  return (
    <div
      ref={containerRef}
      className="flex flex-col h-full bg-background rounded-lg border border-input overflow-hidden"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between p-4 border-b border-input bg-card gap-3">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-foreground truncate flex-1 min-w-0 max-w-full">
            {fileName}
          </h3>
          {totalPages > 0 && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{currentPage}</span>
              <span>/</span>
              <span>{totalPages}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0 whitespace-nowrap">
          {totalPages > 0 && (
            <>
              <div className="flex items-center gap-2 bg-secondary rounded-lg px-3 py-1.5">
                <button
                  onClick={() => setScale(prev => Math.max(prev - 0.1, 0.5))}
                  className="text-foreground hover:text-primary transition-colors text-lg font-bold"
                  title="Zoom out (-)"
                >
                  −
                </button>
                <span className="text-foreground text-xs min-w-12 text-center">
                  {Math.round(scale * 100)}%
                </span>
                <button
                  onClick={() => setScale(prev => Math.min(prev + 0.1, 3))}
                  className="text-foreground hover:text-primary transition-colors text-lg font-bold"
                  title="Zoom in (+)"
                >
                  +
                </button>
              </div>
              <button
                onClick={toggleFullscreen}
                className="flex items-center gap-2 bg-secondary hover:bg-secondary/80 text-foreground text-sm font-medium px-3 py-2 rounded-lg transition-all duration-200"
                title="Toggle fullscreen (F)"
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
            </>
          )}
          <button
            onClick={onDownload}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium px-3 py-2 rounded-lg transition-all duration-200 hover:shadow-md active:scale-95"
          >
            <Download className="w-4 h-4" />
            Download PDF
          </button>
          <button
            onClick={handlePPTXDownload}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium px-3 py-2 rounded-lg transition-all duration-200 hover:shadow-md active:scale-95"
          >
            <Download className="w-4 h-4" />
            Download PPTX
          </button>
        </div>
      </div>

      {/* Preview */}
      <div className="flex-1 relative bg-secondary/30 overflow-hidden">
        {!pdfLibLoaded ? (
          <div className="absolute inset-0 flex items-center justify-center bg-background">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-sm text-muted-foreground">Initializing PDF viewer...</p>
            </div>
          </div>
        ) : isLoading && totalPages === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center bg-background">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-sm text-muted-foreground">Loading presentation...</p>
            </div>
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex items-center justify-center bg-secondary/20">
            <div className="text-center space-y-2 p-4">
              <p className="text-sm font-medium text-foreground">Unable to load preview</p>
              <p className="text-xs text-muted-foreground">{error}</p>
              <p className="text-xs text-muted-foreground">You can still download the file.</p>
            </div>
          </div>
        ) : totalPages > 0 ? (
          <>
            {/* PDF Canvas Display */}
            <div className="h-full flex items-center justify-center p-4">
              {isLoading && currentPage > 0 && (
                <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                    <p className="text-sm text-muted-foreground">Loading page {currentPage}...</p>
                  </div>
                </div>
              )}

              <div className="bg-white shadow-2xl rounded-lg overflow-hidden">
                <canvas
                  ref={canvasRef}
                  className="max-w-full h-auto block"
                />
              </div>
            </div>

            {/* Navigation Buttons Overlay */}
            {!isLoading && (
              <>
                <button
                  onClick={prevPage}
                  disabled={currentPage === 1}
                  className={`absolute left-4 top-1/2 -translate-y-1/2 bg-card/90 hover:bg-card border border-input text-foreground p-3 rounded-full transition-all duration-200 shadow-lg ${currentPage === 1 ? 'opacity-30 cursor-not-allowed' : 'hover:scale-110'
                    }`}
                  title="Previous page (←)"
                >
                  <ChevronLeft className="w-6 h-6" />
                </button>

                <button
                  onClick={nextPage}
                  disabled={currentPage === totalPages}
                  className={`absolute right-4 top-1/2 -translate-y-1/2 bg-card/90 hover:bg-card border border-input text-foreground p-3 rounded-full transition-all duration-200 shadow-lg ${currentPage === totalPages ? 'opacity-30 cursor-not-allowed' : 'hover:scale-110'
                    }`}
                  title="Next page (→ or Space)"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              </>
            )}
          </>
        ) : !fileUrl ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">No preview available</p>
          </div>
        ) : null}
      </div>

      {/* Bottom Controls */}
      {totalPages > 0 && (
        <div className="flex items-center justify-center gap-2 p-4 bg-card border-t border-input flex-shrink-0">
          <button
            onClick={prevPage}
            disabled={currentPage === 1}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${currentPage === 1
              ? 'bg-secondary text-muted-foreground cursor-not-allowed'
              : 'bg-secondary hover:bg-secondary/80 text-foreground'
              }`}
          >
            Previous
          </button>

          {/* Page Dots */}
          <div className="flex items-center gap-1.5 px-4 max-w-md overflow-x-auto">
            {Array.from({ length: Math.min(totalPages, 15) }, (_, i) => {
              const pageNum = i + 1
              const isActive = pageNum === currentPage
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`transition-all duration-200 rounded-full flex-shrink-0 ${isActive
                    ? 'w-8 h-2 bg-primary'
                    : 'w-2 h-2 bg-muted hover:bg-muted-foreground/50'
                    }`}
                  title={`Go to page ${pageNum}`}
                />
              )
            })}
            {totalPages > 15 && (
              <span className="text-muted-foreground text-xs ml-1">+{totalPages - 15}</span>
            )}
          </div>

          <button
            onClick={nextPage}
            disabled={currentPage === totalPages}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${currentPage === totalPages
              ? 'bg-secondary text-muted-foreground cursor-not-allowed'
              : 'bg-secondary hover:bg-secondary/80 text-foreground'
              }`}
          >
            Next
          </button>
        </div>
      )}

      {/* Keyboard Shortcuts Hint */}
      {totalPages > 0 && !isLoading && (
        <div className="absolute bottom-20 right-4 bg-card/90 border border-input text-muted-foreground text-xs px-3 py-2 rounded-lg shadow-lg">
          ← → Space: Navigate | F: Fullscreen | +/−: Zoom
        </div>
      )}
    </div>
  )
}