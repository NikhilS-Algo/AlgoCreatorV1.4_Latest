import React, { useState } from "react";
import { Folder, FolderOpen, FileText, ChevronDown, ChevronRight } from 'lucide-react';

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

const getAllFileIdsInFolder = (folder: Folder): number[] => {
  let fileIds: number[] = [];
  fileIds = fileIds.concat(folder.files.map(file => file.file_id));
  folder.subfolders.forEach(subfolder => {
    fileIds = fileIds.concat(getAllFileIdsInFolder(subfolder));
  });
  return fileIds;
};

const FolderTree = ({ folder, selectedFileIds, expandedFolders, onToggleExpand, onToggleSelection }: {
  folder: Folder;
  selectedFileIds: Set<number>;
  expandedFolders: Set<string>;
  onToggleExpand: (folderName: string) => void;
  onToggleSelection: (item: File | Folder, isSelected: boolean) => void;
}) => {
  const isExpanded = expandedFolders.has(folder.name);

  const allFiles = getAllFileIdsInFolder(folder);
  const selectedCount = allFiles.filter(id => selectedFileIds.has(id)).length;
  const isSelected = allFiles.length > 0 && selectedCount === allFiles.length;
  const isPartiallySelected = selectedCount > 0 && selectedCount < allFiles.length;

  return (
    <div className="pl-4 border-l border-gray-200">
      {/* Folder Row */}
      <div className="flex items-center space-x-2 py-1">
        <input
          type="checkbox"
          className="form-checkbox h-4 w-4 text-amber-600 rounded cursor-pointer flex-shrink-0"
          checked={isSelected}
          onChange={() => onToggleSelection(folder, !isSelected)}
          ref={input => {
            if (input) {
              input.indeterminate = isPartiallySelected;
            }
          }}
        />
        <div 
          className="flex items-center cursor-pointer flex-grow overflow-hidden" 
          onClick={() => onToggleExpand(folder.name)}
          title={folder.description}
        >
          {isExpanded 
            ? <FolderOpen className="w-4 h-4 text-gray-500 flex-shrink-0" /> 
            : <Folder className="w-4 h-4 text-gray-500 flex-shrink-0" />}
          <span className="ml-2 font-medium text-gray-800 truncate">{folder.name}</span>
          {!isExpanded 
            ? <ChevronRight className="w-4 h-4 text-gray-500 flex-shrink-0 ml-1" />
            : <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0 ml-1" />}
        </div>
      </div>
      
      {/* Expanded Content */}
      {isExpanded && (
        <>
          {/* Render subfolders recursively (now before files) */}
          {folder.subfolders.map(subfolder => (
            <FolderTree
              key={subfolder.name}
              folder={subfolder}
              selectedFileIds={selectedFileIds}
              expandedFolders={expandedFolders}
              onToggleExpand={onToggleExpand}
              onToggleSelection={onToggleSelection}
            />
          ))}
          {/* Render files */}
          {folder.files.map(file => {
            const fileIsSelected = selectedFileIds.has(file.file_id);
            return (
              <div key={file.file_id} className="flex items-center space-x-2 py-1 pl-6 overflow-hidden">
                <input
                  type="checkbox"
                  className="form-checkbox h-4 w-4 text-amber-600 rounded cursor-pointer flex-shrink-0"
                  checked={fileIsSelected}
                  onChange={() => onToggleSelection(file, !fileIsSelected)}
                />
                <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <span className="text-sm text-gray-700 truncate">{file.name}</span>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
};

export default FolderTree;