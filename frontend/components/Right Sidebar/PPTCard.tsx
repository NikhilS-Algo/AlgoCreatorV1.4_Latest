import React from "react";
import { Card } from "../ui/card";
import { Button } from "../ui/button";
import { Eye, Download } from "lucide-react";
import { Badge } from "../ui/badge";
import pptIcon from "@/public/images/ppt_icon.png";
import pdfIcon from "@/public/images/pdf_icon.png";
import Image from "next/image";
import { formatTimeAgo } from "./FormatTime";

import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import DownloadPDF from "./DownloadPDF";
import ViewPDFButton from "./ViewPDFButton";

export interface Presentation {
  id: number;
  file_name: string;
  file_type: string;
  file_path: string;
  file_size: string;
  creation_date: string;
}

const PPTCard = ({ pptData }: { pptData: Presentation }) => {
  return (
    <Card className="presentation-card border-blue-200/50 hover:shadow-md transition-shadow py-3">
      <div className="px-3 flex items-center justify-between">
        <span className="text-sm truncate">{pptData.file_name.split("_").slice(0, -1).join(" ")} </span>
        <div className="items-center space-x-1 flex">
          <ViewPDFButton file={pptData.file_path} title={pptData.file_name}/>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="text-amber-500 hover:bg-amber-50 p-1"
              >
                <Download className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DownloadPDF file={pptData.file_path} name={pptData.file_name}/>
          </DropdownMenu>
        </div>
      </div>

      <div className="px-3">
        <div className="flex items-center space-x-2 mt-1">
          <Badge
            variant="outline"
            className="text-xs border-violet-200 text-violet-600"
          >
            {pptData.file_type.toUpperCase()}
          </Badge>
          <span className="text-xs text-gray-500">{pptData.file_size}</span>
        </div>
        <p className="text-xs text-blue-600 mt-1 pl-1">{formatTimeAgo(pptData.creation_date)}</p>
      </div>
    </Card>
  );
};

export default PPTCard;
