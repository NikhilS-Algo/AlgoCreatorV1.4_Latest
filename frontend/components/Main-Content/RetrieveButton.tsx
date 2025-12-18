import React, { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { addPresentation, Presentation } from "@/redux/features/outputs/presentationsSlice";
import { selectSelectedDateRange } from "@/redux/features/filters/selectedDateRangeSlice";
import { selectSelectedFiles } from "@/redux/features/filters/selectedFilesSlice";
import { useToast } from "@/hooks/use-toast";
import { useAxios } from "@/hooks/useAxios";

interface retrieveResponse {
  slide_metadata: string;
  pdf_url: string;
}

const RetrieveButton = () => {
  const RETRIVE_API_URL = process.env.NEXT_PUBLIC_RETRIEVAL_API_URL;
  const DOWNLOAD_FILE_API_URL = process.env.NEXT_PUBLIC_DOWNLOAD_PDF_API_URL;
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const selectedDateRange = useAppSelector(selectSelectedDateRange);
  const selectedFiles = useAppSelector(selectSelectedFiles);

  const {
    data: retrieveData,
    error: retrieveError,
    loaded: retrieveLoaded,
    callAPI: callRetrieveAPI,
    cancel: cancelRetrieve,
  } = useAxios<retrieveResponse>();

  const {
    data: downloadData,
    error: downloadError,
    loaded: downloadLoaded,
    callAPI: callDownloadAPI,
    cancel: cancelDownload,
  } = useAxios();


  const handleRetrieveDocument = async () => {
    toast({
      variant: "loading",
      title: "Generating PPT",
      description: "Please wait while we generate your presentation...",
      duration: 10000,
    });

    console.log("selected_files: ", selectedFiles);
    
    const creation_start = selectedDateRange.from;
    const creation_end = selectedDateRange.to;
    const query_text = "Empty Message";
    const num_of_slides = 12;
    const queries = [{ query_text, num_of_slides }];
    const tags = [["Tag1", "Tag2"]];

    const payload = {
      date_range: {
        creation_start,
        creation_end,
        modification_start: creation_start,
        modification_end: creation_end,
      },
      queries,
      tags,
      files: selectedFiles,
    };

    if (RETRIVE_API_URL) {
      await callRetrieveAPI(RETRIVE_API_URL, "POST", payload, {
        "Content-Type": "application/json",
        accept: "application/json",
      });
    }
    else {
      toast({        
        variant: "destructive",
        title: "API Error",
        description: "Retrieval API URL is not defined.",
        duration: 3000,
      });
      return;
      
    }
  };

  const handleDownloadFile = async (fileUrl: string) => {
    const query = `${DOWNLOAD_FILE_API_URL}?file_path=${encodeURIComponent(fileUrl)}`
    const payload = {
      file_path: fileUrl,
    };
      
    await callDownloadAPI(query, "GET", {}, {}, "blob");
  }

  useEffect(() => {
    if (retrieveLoaded) {
      if (retrieveError) {
        toast({
          variant: "destructive",
          title: "Error",
          description: "Error getting PPT!",
          duration: 4000,
        });
        return;
      } else if (retrieveData) {
        handleDownloadFile(retrieveData.pdf_url);
      }
    }
  }, [retrieveData, retrieveError, retrieveLoaded, dispatch, toast]);

    
  useEffect(() => {
    if (downloadLoaded) {
      if (downloadError) {
        toast({
          variant: "destructive",
          title: "Error",
          description: "Error Generating PPT!",
          duration: 4000,
        });
        return;
      } else if (downloadData) {
        const blob = new Blob([downloadData], { type: "application/pdf" });
        const url = window.URL.createObjectURL(blob);
        const newPPT = {
          id: Math.floor(Math.random() * 1000000),
          file_name: "Generated PPT",
          file_type: "ppt",
          file_path: retrieveData?.pdf_url || "",
          file_size: "4mb",
          creation_date: new Date().toISOString().split("T")[0],
        };
        dispatch(addPresentation(newPPT));
        toast({
          variant: "default",
          title: "Success!",
          description: "PPT Generated Successfully!",
          duration: 3000, 
        });
      }
    }
  }, [downloadData, downloadError, downloadLoaded, dispatch, toast, retrieveData]);
  

  return (
    <Button
      size="sm"
      className="bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 transition-all duration-150 shadow-sm"
      onClick={handleRetrieveDocument}
    >
      <Search className="h-4 w-4" />
    </Button>
  );
};

export default RetrieveButton;
