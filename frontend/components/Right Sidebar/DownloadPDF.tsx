import React, { useEffect, useState } from "react";
import {
  DropdownMenuItem,
  DropdownMenuContent,
} from "@/components/ui/dropdown-menu";
import Image from "next/image";
import pptIcon from "@/public/images/ppt_icon.png";
import pdfIcon from "@/public/images/pdf_icon.png";
import { useAxios } from "@/hooks/useAxios";
import { useToast } from "@/hooks/use-toast";

interface Presentation {
  file: string;
  name: string;
}

const DownloadFile = ({ file, name }: Presentation) => {
  const {
    data: fileData,
    loaded: fileLoaded,
    error: fileError,
    callAPI: callFileAPI,
  } = useAxios();

  const {
    data: pptData,
    loaded: pptLoaded,
    error: pptError,
    callAPI: callPPTAPI,
  } = useAxios();

  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [currentExt, setCurrentExt] = useState<string>("");
  const { toast } = useToast();

  useEffect(() => {
    let blobData: any = null;
    if (fileLoaded && fileData && currentExt === "pdf") {
      blobData = fileData;
    }
    if (pptLoaded && pptData && currentExt === "pptx") {
      blobData = pptData;
    }

    if (blobData) {
      const blob = new Blob([blobData], {
        type:
          currentExt === "pptx"
            ? "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            : "application/pdf",
      });
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);
    }
  }, [fileData, fileLoaded, pptData, pptLoaded, currentExt]);

  useEffect(() => {
    if (downloadUrl && currentExt) {
      const a = document.createElement("a");
      a.href = downloadUrl;

      let cleanName = name;
      if (currentExt === "pptx" && cleanName.toLowerCase().endsWith(".pdf")) {
        cleanName = cleanName.slice(0, -4);
      }

      a.download = `${cleanName}.${currentExt}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      setDownloadUrl(null);

      toast({
        variant: "default",
        title: "Download Successful",
        description: `Your file has been downloaded.`,
        duration: 3000,
      });
    }
  }, [downloadUrl, currentExt, name, toast]);

  useEffect(() => {
    const error = fileError || pptError;
    if (error) {
      toast({
        variant: "destructive",
        title: "Download Failed",
        description:
          "An error occurred while downloading the file. Please try again.",
        duration: 3000,
      });
    }
  }, [fileError, pptError, toast]);

  const fetchAndDownloadPDF = async () => {
    if (file) {
      setCurrentExt("pdf");
      toast({
        variant: "loading",
        title: "Fetching PDF",
        description: "Please wait while we prepare your download...",
        duration: 60000,
      });
      const API_URL = process.env.NEXT_PUBLIC_DOWNLOAD_PDF_API_URL;
      const query = `${API_URL}?file_path=${encodeURIComponent(file)}`;
      await callFileAPI(query, "GET", {}, {}, "blob");
    }
  };

  const fetchAndDownloadPPT = async () => {
    setCurrentExt("pptx");
    toast({
      variant: "loading",
      title: "Generating PPTX",
      description: "Please wait while we generate your presentation...",
      duration: 60000,
    });
    const API_URL = "http://127.0.0.1:8000/retrieval/download_pptx";
    const payload = {
      file_name: name,
    };
    await callPPTAPI(API_URL, "POST", payload, {}, "blob");
  };

  return (
    <DropdownMenuContent align="end">
      <DropdownMenuItem onClick={fetchAndDownloadPDF}>
        <Image src={pdfIcon} alt="PDF Icon" className="h-6 w-6 mr-2" />
        PDF
      </DropdownMenuItem>
      <DropdownMenuItem onClick={fetchAndDownloadPPT}>
        <Image src={pptIcon} alt="PPTX Icon" className="h-6 w-6 mr-2" />
        PPTX
      </DropdownMenuItem>
    </DropdownMenuContent>
  );
};

export default DownloadFile;