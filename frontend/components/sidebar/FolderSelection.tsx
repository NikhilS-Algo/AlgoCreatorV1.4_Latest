import React, { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import { selectFoldersData } from "@/redux/features/filters/FetchedFoldersSlice";
import { selectSelectedFiles, appendFiles, removeFiles, appendFile, removeFile } from "@/redux/features/filters/selectedFilesSlice";
import { Folder, FolderOpen, FileText} from 'lucide-react';
import FolderTree from "./FolderTree";

interface File {
  file_id: number;
  name: string;
  num_slides: number;
  tags: string[];
}

interface Folder {
  name: string;
  description: string;
  subfolders: Folder[];
  files: File[];
}

interface FoldersData {
  root_node: Folder;
}

const getAllFileIdsInFolder = (folder: Folder): number[] => {
  let fileIds: number[] = [];
  fileIds = fileIds.concat(folder.files.map(file => file.file_id));
  // Recursively get files from subfolders
  folder.subfolders.forEach(subfolder => {
    fileIds = fileIds.concat(getAllFileIdsInFolder(subfolder));
  });
  return fileIds;
};

const FolderSelection = () => {
  const foldersData: FoldersData = useAppSelector(selectFoldersData);
  const selectedFiles = useAppSelector(selectSelectedFiles);
  const dispatch = useAppDispatch();

  const selectedFileIds = new Set(selectedFiles);

  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  const handleToggleExpand = (folderName: string) => {
    setExpandedFolders(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(folderName)) {
        newExpanded.delete(folderName);
      } else {
        newExpanded.add(folderName);
      }
      return newExpanded;
    });
  };

  const handleToggleSelection = (item: File | Folder, isSelected: boolean) => {
    // If it's a file
    if ('file_id' in item) {
      if (isSelected) {
        dispatch(appendFile(item.file_id));
      } else {
        dispatch(removeFile(item.file_id));
      }
    } 
    // If it's a folder
    else {
      const allFileIds = getAllFileIdsInFolder(item);
      if (isSelected) {
        dispatch(appendFiles(allFileIds));
      } else {
        dispatch(removeFiles(allFileIds));
      }
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg shadow-sm">
        <Badge
          variant="secondary"
          className="text-xs bg-amber-100 text-amber-700 border-0"
        >
          {selectedFiles.length} files selected
        </Badge>
      <div className="flex items-center space-x-2 mb-4">
      </div>

      {foldersData.root_node.name !== "" && (
        <FolderTree
          folder={foldersData.root_node}
          selectedFileIds={selectedFileIds}
          expandedFolders={expandedFolders}
          onToggleExpand={handleToggleExpand}
          onToggleSelection={handleToggleSelection}
        />
      )}
    </div>
  );
};

export default FolderSelection;
