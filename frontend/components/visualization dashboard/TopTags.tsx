"use client";
import React from "react";
import { Tag } from "lucide-react";
import { useAppSelector } from "@/redux/hooks";
import { selectSelectedFiles } from "@/redux/features/filters/selectedFilesSlice";
import { selectFoldersData } from "@/redux/features/filters/FetchedFoldersSlice";
import {
  ApiFolderNode,
  FileNode,
} from "@/redux/features/filters/FetchedFoldersSlice";

const getAllFiles = (node: ApiFolderNode, allFiles: FileNode[]): void => {
  if (!node) return;

  if (node.files && Array.isArray(node.files)) {
    allFiles.push(...node.files);
  }

  if (node.subfolders && Array.isArray(node.subfolders)) {
    node.subfolders.forEach((subfolder) => getAllFiles(subfolder, allFiles));
  }
};

const TopTags = () => {
  // Use Redux selectors to get the selected files and all folder data
  const selectedFiles = useAppSelector(selectSelectedFiles);
  const { root_node } = useAppSelector(selectFoldersData);

  // Get a flat list of all files from the Redux state's folder tree
  const allFiles: FileNode[] = [];
  getAllFiles(root_node, allFiles);

  // Filter all files to get only the selected ones
  const selectedFilesData = allFiles.filter((file) =>
    selectedFiles.includes(file.file_id)
  );

  // Extract all tags from the selected files
  const allTags: string[] = selectedFilesData.flatMap((file) => file.tags);

  // Calculate the frequency of each tag
  const tagFrequency: Record<string, number> = {};
  allTags.forEach((tag) => {
    // Check if the tag is a non-empty string before processing
    if (typeof tag === "string" && tag.trim().length > 0) {
      tagFrequency[tag.toUpperCase()] =
        (tagFrequency[tag.toUpperCase()] || 0) + 1;
    }
  });

  // Sort the tags by frequency and get the top 5
  const topTags = Object.entries(tagFrequency)
    .sort(([, countA], [, countB]) => countB - countA)
    .slice(0, 5);

  return (
    <div className="flex-1 w-full bg-white p-4 rounded-xl shadow-lg" id='top-tag'>
      <h3 className="text-lg font-bold text-gray-800 mb-4">Top 5 Tags</h3>
      <ul className="space-y-2">
        {topTags.map(([tag, count]) => (
          <li
            key={tag}
            className="flex justify-between items-center px-3 py-2 rounded-lg hover:bg-gray-100 transition"
          >
            <span className="text-gray-700 text-sm font-medium truncate">
              {tag}
            </span>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="bg-blue-100 text-blue-600 text-xs font-semibold px-2 py-0.5 rounded-full min-w-[28px] text-center">
                {count}
              </span>
              <Tag className="text-blue-400" size={18} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TopTags;
