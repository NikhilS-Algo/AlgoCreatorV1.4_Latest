import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from "react";
import { createRoot } from "react-dom/client";
import { Undo2 } from "lucide-react";
import {
  selectSelectedFiles,
  appendFile,
  appendFiles,
  removeFile,
  removeFiles,
  SelectedFilesState,
} from "@/redux/features/filters/selectedFilesSlice";
import { selectFoldersData, FoldersData, ApiFolderNode, FileNode } from "@/redux/features/filters/FetchedFoldersSlice";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";

const START_FOLDER_NAME = "Algo_Org_PPTs";

// Updated interfaces to work with Redux state structure
interface ChartNode {
  name: string;
  children?: ChartNode[];
  value?: number;
  slideCount: number;
  fileCount: number;
  isFile?: boolean;
  file_id?: number; // Use file_id instead of filePath for consistency with Redux
}

interface SunburstChartProps {
  onFolderSelect?: (
    folderData: any[],
    folderName: string,
    folderPath: string
  ) => void;
  focusedFolderName: string,
  setFocusedFolderName: React.Dispatch<React.SetStateAction<string>>
}

// Helper function to recursively get all file IDs within a folder
const getAllFileIds = (node: ApiFolderNode | FileNode): number[] => {
  if ((node as FileNode).file_id !== undefined) {
    return [(node as FileNode).file_id];
  }
  
  let ids: number[] = [];
  const folderNode = node as ApiFolderNode;
  if (folderNode.files) {
    ids = [...ids, ...folderNode.files.map(file => file.file_id)];
  }
  if (folderNode.subfolders) {
    folderNode.subfolders.forEach(subfolder => {
      ids = [...ids, ...getAllFileIds(subfolder)];
    });
  }
  return ids;
};

// Helper function to transform Redux folder data into chart format
const transformFolderData = (node: ApiFolderNode | FileNode): ChartNode => {
  if ((node as FileNode).file_id !== undefined) {
    // It's a file node
    const fileNode = node as FileNode;
    return {
      name: fileNode.name,
      value: 1,
      slideCount: fileNode.num_slides || 0,
      fileCount: 1,
      isFile: true,
      file_id: fileNode.file_id,
    };
  }

  // It's a folder node
  const folderNode = node as ApiFolderNode;
  let children: ChartNode[] = [];
  let totalSlides = 0;
  let totalFiles = 0;

  // Process files within the folder
  if (folderNode.files && folderNode.files.length > 0) {
    folderNode.files.forEach(file => {
      const fileChartNode = transformFolderData(file);
      children.push(fileChartNode);
      totalSlides += fileChartNode.slideCount;
      totalFiles += 1;
    });
  }

  // Process subfolders
  if (folderNode.subfolders && folderNode.subfolders.length > 0) {
    folderNode.subfolders.forEach(subfolder => {
      const subfolderChartNode = transformFolderData(subfolder);
      children.push(subfolderChartNode);
      totalSlides += subfolderChartNode.slideCount;
      totalFiles += subfolderChartNode.fileCount;
    });
  }

  return {
    name: folderNode.name,
    children: children.length > 0 ? children : undefined,
    value: children.length === 0 ? 1 : undefined,
    slideCount: totalSlides,
    fileCount: totalFiles,
    isFile: false,
  };
};

// Updated SunburstChart component
const SunburstChart: React.FC<SunburstChartProps> = ({
  onFolderSelect, focusedFolderName, setFocusedFolderName
}) => {
  const selectedFiles: SelectedFilesState = useAppSelector(selectSelectedFiles);
  const foldersData: FoldersData = useAppSelector(selectFoldersData);
  const dispatch = useAppDispatch();
  
  // Use ref to always have the latest selectedFiles state
  const selectedFilesRef = useRef(selectedFiles);
  selectedFilesRef.current = selectedFiles;
  
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);
  const centerIconRootRef = useRef<any>(null);
  const [SunburstComponent, setSunburstComponent] = useState<any>(null);
  const [isClient, setIsClient] = useState(false);

  // Load Sunburst component only on client side
  useEffect(() => {
    setIsClient(true);
    const loadSunburst = async () => {
      const SunburstModule = await import("sunburst-chart");
      setSunburstComponent(() => SunburstModule.default);
    };
    loadSunburst();
  }, []);

  // Effect to prevent the default right-click context menu
  useEffect(() => {
    const chartDiv = chartRef.current;
    if (chartDiv) {
      const handleContext = (e: MouseEvent) => e.preventDefault();
      chartDiv.addEventListener("contextmenu", handleContext);
      return () => {
        chartDiv.removeEventListener("contextmenu", handleContext);
      };
    }
  }, [isClient]);

  // Function to add center icon overlay
  const addCenterIcon = useCallback(() => {
    if (!chartRef.current) return;

    // Remove existing center icon if any
    const existingIcon = chartRef.current.querySelector('.center-back-icon');
    if (existingIcon) {
      if (centerIconRootRef.current) {
        centerIconRootRef.current.unmount();
        centerIconRootRef.current = null;
      }
      existingIcon.remove();
    }

    // Create center icon container
    const centerIcon = document.createElement('div');
    centerIcon.className = 'center-back-icon';
    
    centerIcon.style.cssText = `
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #666;
      pointer-events: none;
      z-index: 10;
      background: rgba(255, 255, 255, 0.9);
      padding: 8px;
      border-radius: 50%;
      border: 1px solid #ddd;
      user-select: none;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      display: flex;
      align-items: center;
      justify-content: center;
    `;

    // Make the chart container relative positioned
    chartRef.current.style.position = 'relative';
    chartRef.current.appendChild(centerIcon);

    // Use React's createRoot to render the Lucide icon
    centerIconRootRef.current = createRoot(centerIcon);
    centerIconRootRef.current.render(<Undo2 size={20} />);
  }, []);

  // Transform Redux data into chart format
  const chartData = useMemo(() => {
    if (!foldersData.root_node.name) {
      return { name: "__root__", value: 0, children: [] };
    }
    
    const transformedData = transformFolderData(foldersData.root_node);
    return {
      name: "__root__",
      value: 0,
      children: [transformedData],
    };
  }, [foldersData.root_node]);

  // Function to find a node by name in the chart data
  const findNodeByName = useCallback((nodes: ChartNode[], name: string): ChartNode | null => {
    for (const node of nodes) {
      if (node.name === name) return node;
      if (node.children) {
        const result = findNodeByName(node.children, name);
        if (result) return result;
      }
    }
    return null;
  }, []);

  // Memoized function to find folder nodes to avoid recreation on each render
  const findFolderNode = useCallback((node: ApiFolderNode | FileNode, targetName: string): ApiFolderNode | null => {
    if (node.name === targetName && (node as ApiFolderNode).subfolders !== undefined) {
      return node as ApiFolderNode;
    }
    if ((node as ApiFolderNode).subfolders) {
      for (const subfolder of (node as ApiFolderNode).subfolders) {
        const result = findFolderNode(subfolder, targetName);
        if (result) return result;
      }
    }
    return null;
  }, []);

  // Centralized function to determine node color
  const getNodeColor = useCallback(
    (d: any) => {
      // Selected files are green
      if (d.isFile && d.file_id && selectedFiles.includes(d.file_id)) {
        return "#4CAF50";
      }

      // Check if folder has all files selected
      if (!d.isFile && d.name !== "__root__") {
        const folderNode = findFolderNode(foldersData.root_node, d.name);
        if (folderNode) {
          const allFileIds = getAllFileIds(folderNode);
          if (allFileIds.length > 0 && allFileIds.every(id => selectedFiles.includes(id))) {
            return "#4CAF50"; // Green for fully selected folders
          }
        }
      }

      // Default color for everything else
      const hash = d.name.split("").reduce((a: number, b: string) => {
        a = (a << 5) - a + b.charCodeAt(0);
        return a & a;
      }, 0);
      const hue = Math.abs(hash) % 360;
      return `hsl(${hue}, 60%, 85%)`;
    },
    [selectedFiles, foldersData.root_node, findFolderNode]
  );

  const updateChartColors = useCallback(() => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.color(getNodeColor);
    }
  }, [getNodeColor]);

  // Function to handle returning to the root folder view
  const handleGoToRoot = useCallback(() => {
    if (
      chartInstanceRef.current &&
      chartData.children &&
      chartData.children.length > 0
    ) {
      const rootNode = chartData.children[0];
      chartInstanceRef.current.focusOnNode(rootNode);

      // Update the focused folder name state
      setFocusedFolderName(rootNode.name);

      // Update the side panels if callback is provided
      if (onFolderSelect && rootNode) {
        onFolderSelect([rootNode], rootNode.name, "/");
      }
    }
  }, [chartData, onFolderSelect, setFocusedFolderName]);

  // Function to clear all selected files
  const handleClearSelection = useCallback(() => {
    dispatch(removeFiles(selectedFiles));
    updateChartColors();
  }, [dispatch, selectedFiles, updateChartColors]);

  // Handler for right-clicking on a node (file or folder)
  const handleRightClick = useCallback(
    (node: any) => {
      if (!node || node.name === "__root__") return;

      // Use ref to get the latest selectedFiles state to avoid stale closure
      const currentSelectedFiles = selectedFilesRef.current;

      // Handle file selection/deselection
      if (node.isFile && node.file_id) {
        if (currentSelectedFiles.includes(node.file_id)) {
          // File is selected, so deselect it
          dispatch(removeFile(node.file_id));
        } else {
          // File is not selected, so select it
          dispatch(appendFile(node.file_id));
        }
        return;
      }

      // Handle folder selection/deselection
      if (!node.isFile) {
        const folderNode = findFolderNode(foldersData.root_node, node.name);
        if (!folderNode) return;

        const allFileIds = getAllFileIds(folderNode);
        if (allFileIds.length === 0) return;

        // Check if ALL files in the folder are currently selected using fresh state
        const areAllSelected = allFileIds.every(id => currentSelectedFiles.includes(id));

        if (areAllSelected) {
          // All files are selected, so deselect ALL files in the folder
          dispatch(removeFiles(allFileIds));
        } else {
          // Not all files are selected, so select ALL files in the folder
          // We need to add all files, not just the unselected ones
          // First remove any currently selected files from this folder to avoid duplicates
          const currentlySelectedFromFolder = allFileIds.filter(id => currentSelectedFiles.includes(id));
          if (currentlySelectedFromFolder.length > 0) {
            dispatch(removeFiles(currentlySelectedFromFolder));
          }
          // Then add all files from the folder
          dispatch(appendFiles(allFileIds));
        }
      }
    },
    [foldersData.root_node, dispatch, findFolderNode] // Removed selectedFiles from dependencies
  );

  // Effect to render the chart (only when data changes)
  useEffect(() => {
    if (
      !isClient ||
      !SunburstComponent ||
      !foldersData.root_node.name ||
      !chartRef.current
    )
      return;

    if (chartRef.current) chartRef.current.innerHTML = "";

    const myChart = SunburstComponent()
      .data(chartData)
      .width(550)
      .height(550)
      .color(getNodeColor)
      .tooltipTitle((d: any) => (d.name === "__root__" ? "" : d.name))
      .tooltipContent((d: any, node: any) => {
        if (node.data.name === "__root__") return "";
        const slideCount = node.data.slideCount ?? 0;
        const fileCount = node.data.fileCount ?? (node.data.isFile ? 1 : 0);
        let content = `Name: ${node.data.name}<br/>Files: ${fileCount}<br/>Slides: ${slideCount}`;
        return content;
      })
      .onClick((node: any) => {
        if (!node || node.name === "__root__") {
          handleGoToRoot();
          return;
        }

        // Update the focused folder name state when clicking on any node
        if (!node.isFile) {
          setFocusedFolderName(node.name);
        }

        // For folders, update the side panel before focusing
        if (!node.isFile && onFolderSelect) {
          onFolderSelect([node], node.name, `/${node.name}`);
        }

        // For both files and folders, focus on the node when left-clicked (zoom functionality)
        myChart.focusOnNode(node);
      })
      .onRightClick(handleRightClick);

    chartInstanceRef.current = myChart;

    if (chartRef.current) {
      myChart(chartRef.current);
      // Set initial focus on the root folder
      if (chartData.children && chartData.children.length > 0) {
        myChart.focusOnNode(chartData.children[0]);
        // Set initial focused folder name
        setFocusedFolderName(chartData.children[0].name);
      }
      
      // Add center icon after chart is rendered
      setTimeout(() => {
        addCenterIcon();
      }, 100);
    }

    // Initialize side panels with the first folder's data
    if (chartData.children && chartData.children.length > 0 && onFolderSelect) {
      const firstFolder = chartData.children[0];
      onFolderSelect([firstFolder], firstFolder.name, `/${firstFolder.name}`);
    }
  }, [
    isClient,
    SunburstComponent,
    chartData, // Only depend on chartData, not individual handlers
    foldersData.root_node.name, // Only the name to avoid deep comparison
    setFocusedFolderName, // Add this dependency
    addCenterIcon, // Add this dependency
  ]);

  // Separate effect to update colors when selected files change - this avoids full re-render
  useEffect(() => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.color(getNodeColor);
    }
  }, [selectedFiles]); // Only depend on selectedFiles, use getNodeColor directly

  if (!foldersData.root_node.name) {
    return (
      <div className="flex items-center justify-center h-full text-lg text-gray-500">
        Loading folder data...
      </div>
    );
  }

  return (
    <div className="SunBurst-container">
      <div className="flex flex-col items-center">
        <h3 className="text-xl font-semibold mb-2">PPT Folder Structure</h3>

        {/* Instructions */}
        <p className="text-sm text-gray-600 mb-4 text-center">
          🖱️ <span className="font-medium">Left-click</span> to zoom into folder/file,<br />
          🖱️ <span className="font-medium">Right-click</span> to select/ deselect folder/file.<br />
          🖱️ <span className="font-medium">Click center</span> to zoom out.
        </p>

        <div className="flex flex-col gap-2 items-center">
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={handleGoToRoot}
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mb-2"
            >
              Go to Root Folder
            </button>
            <button
              className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded mb-2"
              onClick={handleClearSelection}
              disabled={selectedFiles.length === 0}
            >
              Clear Selection
            </button>
            <button
              className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded mb-2 justify-center flex"
              onClick={() => console.log("Selected files:", selectedFiles)}
            >
              Selected Files ({selectedFiles.length})
            </button>
          </div>
        </div>

        {isClient ? (
          <div ref={chartRef} className="w-[550px] h-[550px]" />
        ) : (
          <div className="w-[550px] h-[550px] flex items-center justify-center text-gray-500 border border-gray-200 rounded-md bg-gray-50">
            <span className="text-center">
              ⏳<br />
              Loading chart...
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default SunburstChart;