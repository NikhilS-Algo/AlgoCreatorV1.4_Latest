import pptDataJson from "@/data/new_updated_data.json";
import {
  clearSelection,
  appendFiles,
} from "@/redux/features/filters/selectedFilesSlice";
import { AppDispatch } from "@/redux/store";

interface PPTData {
  file_id: string;
  pptx_name: string;
  pptx_path: string;
  last_mod_date: string;
  creation_date: string;
  slide_details: slide[];
}

interface slide {
  "Tags associated": string[];
}

interface FileNode {
  name: string;
  file_id: number;
  num_slides: number;
  tags: string[];
}

interface ApiFolderNode {
  name: string;
  description: string;
  subfolders: ApiFolderNode[];
  files: FileNode[];
}

interface FoldersData {
  root_node: ApiFolderNode;
  //   first_level_folders: string[];
}

const pptData = pptDataJson as PPTData[];
const ROOT_FOLDER = "/content/drive/MyDrive/GenAI (UI UX)/Algo_Org_PPTs";
const summaries: { [key: string]: string } = {};

const parseDate = (dateStr: string): Date | null => {
  if (!dateStr) return null;
  return new Date(dateStr);
};

const isDateWithinRange = (
  date: Date | null,
  start: Date | null,
  end: Date | null
): boolean => {
  if (!date) return false;
  const targetDate = date.getTime();
  const startDate = start ? start.getTime() : -Infinity;
  const endDate = end ? end.getTime() : Infinity;
  return targetDate >= startDate && targetDate <= endDate;
};

const getFileType = (fileName: string): string => {
  const parts = fileName.split(".");
  return parts.length > 1 ? parts.pop()!.toLowerCase() : "";
};

export const getFilesTree = (
  creation_start: string,
  creation_end: string,
  modification_start: string,
  modification_end: string,
  dispatch: AppDispatch
): FoldersData | null => {
  dispatch(clearSelection());
  const cs = parseDate(creation_start);
  const ce = parseDate(creation_end);
  const ms = parseDate(modification_start);
  const me = parseDate(modification_end);

  const newIds = [];

  const rootNode: ApiFolderNode = {
    name: "Algo_Org_PPTs",
    description:
      summaries[ROOT_FOLDER] ||
      "Root folder containing various technology-related projects.",
    subfolders: [],
    files: [],
  };

  for (const item of pptData) {
    const pptxPath = item.pptx_path;
    if (!pptxPath || !pptxPath.includes(ROOT_FOLDER)) {
      continue;
    }

    const cdate = parseDate(item.creation_date);
    const mdate = parseDate(item.last_mod_date);

    // Date filtering
    if (
      (cs && ce && !isDateWithinRange(cdate, cs, ce)) ||
      (ms && me && !isDateWithinRange(mdate, ms, me))
    ) {
      continue;
    }

    // Get relative path and parts
    const relPath = pptxPath.split(ROOT_FOLDER, 2)[1].replace(/^[/\\]+/, "");
    const parts = relPath.split(/[/\\]+/);
    const fileName = parts.pop();
    if (!fileName) continue;

    let currentNode = rootNode;
    for (const part of parts) {
      if (!part) continue;
      let subfolder = currentNode.subfolders.find((sf) => sf.name === part);
      if (!subfolder) {
        subfolder = {
          name: part,
          description: summaries[part] || `Description for ${part}.`,
          subfolders: [],
          files: [],
        };
        currentNode.subfolders.push(subfolder);
      }
      currentNode = subfolder;
    }

    // Extract tags from slide_details
    currentNode.files.push({
      name: fileName,
      file_id: parseInt(item.file_id, 10),
      num_slides: item.slide_details.length,
      tags: Array.from(
        new Set(item.slide_details.flatMap((slide) => slide["Tags associated"]))
      ),
    });
    newIds.push(parseInt(item.file_id, 10));
  }

  dispatch(appendFiles(newIds));
  updateJson(newIds, creation_start, creation_end, modification_start, modification_end);

  console.log(rootNode);
  return { root_node: rootNode };
};

const updateJson = async (
  selectedFiles: number[],
  creation_start: string,
  creation_end: string,
  modification_start: string,
  modification_end: string
) => {
  try {
    const res = await fetch("/v4beta/api/update-filters", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_files: selectedFiles,
        date_range: {
          creation_start,
          creation_end,
          modification_start,
          modification_end,
        },
      }),
    });
    if (!res.ok) {
      console.log("Error updating filters:");
    }
  } catch (error) {
    console.log("Error updating filters:", error);
  }
};
