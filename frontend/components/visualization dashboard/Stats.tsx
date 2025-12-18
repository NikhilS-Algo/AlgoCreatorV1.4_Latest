'use client';
import React, { useEffect, useRef, useState } from 'react';
import { FileText, Calendar, Folder, Tag } from 'lucide-react';
import { useAppSelector } from "@/redux/hooks";
import { selectSelectedFiles } from '@/redux/features/filters/selectedFilesSlice';
import { selectFoldersData } from '@/redux/features/filters/FetchedFoldersSlice';
import { ApiFolderNode, FileNode } from '@/redux/features/filters/FetchedFoldersSlice';

const getAllFiles = (node: ApiFolderNode, allFiles: FileNode[]): void => {
  if (!node) return;
  
  if (node.files && Array.isArray(node.files)) {
    allFiles.push(...node.files);
  }

  if (node.subfolders && Array.isArray(node.subfolders)) {
    node.subfolders.forEach(subfolder => getAllFiles(subfolder, allFiles));
  }
};

const getAllFileIdsInFolder = (folder: ApiFolderNode): number[] => {
  let fileIds: number[] = [];
  if (folder.files && Array.isArray(folder.files)) {
    fileIds = fileIds.concat(folder.files.map(file => file.file_id));
  }
  if (folder.subfolders && Array.isArray(folder.subfolders)) {
    folder.subfolders.forEach(subfolder => {
      fileIds = fileIds.concat(getAllFileIdsInFolder(subfolder));
    });
  }
  return fileIds;
};

const countSelectedFolders = (node: ApiFolderNode, selectedFiles: number[]): number => {
  let count = 0;
  
  // Get all file IDs for the current node and its children.
  const fileIdsInFolder = getAllFileIdsInFolder(node);
  
  // A folder is considered 'selected' if it contains at least one file and one of those files is selected.
  if (fileIdsInFolder.length > 0) {
    const isSelected = fileIdsInFolder.some(fileId => selectedFiles.includes(fileId));
    if (isSelected) {
      count++;
    }
  }

  // Recursively check subfolders and add their counts.
  if (node.subfolders && Array.isArray(node.subfolders)) {
    node.subfolders.forEach(subfolder => {
      count += countSelectedFolders(subfolder, selectedFiles);
    });
  }
  
  return count;
};

const Stats = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [columns, setColumns] = useState(1);

  // Use Redux selectors to get the selected files and all folder data
  const selectedFiles = useAppSelector(selectSelectedFiles);
  const { root_node } = useAppSelector(selectFoldersData);

  // Collect all files from the Redux state's folder tree
  const allFiles: FileNode[] = [];
  getAllFiles(root_node, allFiles);

  // Filter all files to get only the selected ones.
  const selectedFilesData = allFiles.filter(file => selectedFiles.includes(file.file_id));

  // --- Calculate stats based on selected files ---
  const totalPPTs = selectedFilesData.length;
  let totalSlides = 0;
  const tagsSet = new Set<string>();

  selectedFilesData.forEach((file) => {
    totalSlides += file.num_slides;
    if (file.tags && Array.isArray(file.tags)) {
      file.tags.forEach((tag: string) => {
        if (typeof tag === 'string' && tag.trim().length > 0) {
          tagsSet.add(tag.trim().toUpperCase());
        }
      });
    }
  });

  // Calculate the total number of folders where at least one file is selected.
  const totalFolders = countSelectedFolders(root_node, selectedFiles);

  const totalUniqueTags = tagsSet.size;

  const statsData = [
    {
      title: 'Total Presentations',
      value: allFiles.length,
      subtitle: `${selectedFiles.length} Files Selected`,
      icon: <FileText size={20} />,
      bg: 'bg-blue-100',
      color: 'text-blue-500',
    },
    {
      title: 'Total Slides',
      value: totalSlides,
      subtitle: `~${Math.round(totalSlides / (totalPPTs || 1))} slides per presentation`,
      icon: <Calendar size={20} />,
      bg: 'bg-green-100',
      color: 'text-green-500',
    },
    {
      title: 'Folders',
      value: totalFolders,
      subtitle: 'Organized collections',
      icon: <Folder size={20} />,
      bg: 'bg-purple-100',
      color: 'text-purple-500',
    },
    {
      title: 'Unique Tags',
      value: totalUniqueTags,
      subtitle: 'Different topics covered',
      icon: <Tag size={20} />,
      bg: 'bg-orange-100',
      color: 'text-orange-500',
    },
  ];

  // Watch parent width and set columns
  useEffect(() => {
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const width = entry.contentRect.width;

        if (width >= 1000) {
          setColumns(4);
        } else if (width >= 500) {
          setColumns(2);
        } else {
          setColumns(1);
        }
      }
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} className="w-full px-10 py-8">
      <div
        className="grid gap-5 justify-center"
        style={{
          gridTemplateColumns: `repeat(${columns}, 1fr)`,
        }}
      >
        {statsData.map((item, idx) => (
          <div
            key={idx}
            id={`stats-card-${idx}`} // Added for tutorial
            className="bg-white rounded-xl shadow-md p-5 h-[160px] flex items-center hover:shadow-xl transition-transform hover:-translate-y-1"
          >
            <div className="flex justify-between items-center w-full">
              <div>
                <h4 className="text-sm text-gray-600">{item.title}</h4>
                <h2 className="text-2xl font-bold text-gray-900 mt-2">{item.value}</h2>
                <p className="text-sm text-gray-500 mt-2">{item.subtitle}</p>
              </div>
              <div
                className={`w-11 h-11 rounded-full flex items-center justify-center ${item.bg} ${item.color}`}
              >
                {item.icon}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Stats;
