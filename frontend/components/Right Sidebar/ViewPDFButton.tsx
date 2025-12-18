import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Eye, Loader2 } from "lucide-react";
import { useAxios } from "@/hooks/useAxios";

interface Presentation {
  file: string;
  title: string;
}

const ViewPDFButton = ({ file, title }: Presentation) => {
  const {
    data: fileData,
    error: fileError,
    loaded: fileLoaded,
    callAPI: callFileAPI,
  } = useAxios();

  const [pdfUrl, setPdfUrl] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (fileLoaded) {
      setIsLoading(false);
      if (!fileError && fileData) {
        const blob = new Blob([fileData], { type: "application/pdf" });
        const url = window.URL.createObjectURL(blob);
        setPdfUrl(url);
      } else {
        console.error("Failed to fetch PDF:", fileError);
        setPdfUrl("");
      }
    }
  }, [fileData, fileError, fileLoaded]);

  useEffect(() => {
    return () => {
      if (pdfUrl) {
        window.URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (open) {
      if (file && !pdfUrl) {
        setIsLoading(true);
        const API_URL = process.env.NEXT_PUBLIC_DOWNLOAD_PDF_API_URL;
        const query = `${API_URL}?file_path=${encodeURIComponent(file)}`;
        callFileAPI(query, "GET", {}, {}, "blob");
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="text-blue-500 hover:bg-blue-50 p-1"
          onClick={(e) => e.stopPropagation()}
        >
          <Eye className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent
        aria-describedby={undefined}
        className="w-[90vw] h-[90vh] max-w-none p-4 flex flex-col"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">{title}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 bg-white rounded-lg h-full overflow-hidden flex items-center justify-center">
          {isLoading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              <span className="text-gray-500">Loading PDF...</span>
            </div>
          ) : pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0"
              title={`${title} PDF Preview`}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-8">
              <div className="text-center space-y-4">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                  <svg
                    className="w-8 h-8 text-red-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900">
                  Unable to View PDF
                </h3>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ViewPDFButton;