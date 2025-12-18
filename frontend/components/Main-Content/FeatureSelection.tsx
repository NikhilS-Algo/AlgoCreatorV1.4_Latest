import React, { useRef, useEffect, useState } from "react";
import { Globe, FileText, Rss, Newspaper, Linkedin, Plus, X } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { setOpenFeatures, selectOpenFeatures } from "@/redux/features/loading/openFeaturesSlice";

const features = [
  { name: 'Web Search', icon: Globe, color: 'text-blue-500', activeColor: 'bg-blue-500 text-white' },
  { name: 'Research Papers', icon: FileText, color: 'text-green-600', activeColor: 'bg-green-600 text-white' },
  { name: 'Blogs', icon: Rss, color: 'text-orange-500', activeColor: 'bg-orange-500 text-white' },
  { name: 'News', icon: Newspaper, color: 'text-red-500', activeColor: 'bg-red-500 text-white' },
  { name: 'LinkedIn Posts', icon: Linkedin, color: 'text-sky-600', activeColor: 'bg-sky-600 text-white' },
];

const FeatureSelection = () => {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector(selectOpenFeatures);

  const handleFeatureToggle = (featureName: string) => {
    setSelectedFeatures((prevSelected) => {
      if (prevSelected.includes(featureName)) {
        return prevSelected.filter((name) => name !== featureName);
      }
      return [...prevSelected, featureName];
    });
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;

      if (target.closest(".shepherd-element")) {
        return;
      }

      if (popoverRef.current && !popoverRef.current.contains(target)) {
        dispatch(setOpenFeatures(false));
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dispatch]);

  return (
    <div className="relative" ref={popoverRef}>
      {
        <div
          id="chat-features"
          className={
            isOpen
              ? "absolute bottom-full left-2 mb-2 w-max max-w-sm p-3 bg-white rounded-lg shadow-xl border border-gray-200"
              : "hidden"
          }
        >
          <div className="flex flex-col gap-2">
            {features.map((feature) => {
              const Icon = feature.icon;
              const isSelected = selectedFeatures.includes(feature.name);

              return (
                <div
                  key={feature.name}
                  onClick={() => handleFeatureToggle(feature.name)}
                  // MODIFICATION 2: Add w-full and change rounding
                  className={`flex items-center space-x-2 p-2 px-3 rounded-lg cursor-pointer transition-colors w-full ${isSelected
                      ? feature.activeColor
                      : "bg-white text-gray-700 hover:bg-gray-200"
                    }`}
                >
                  <Icon
                    className={`h-5 w-5 ${isSelected ? "" : feature.color}`}
                    strokeWidth={1.75}
                  />
                  <span>{feature.name}</span>
                </div>
              );
            })}
          </div>
        </div>
      }

      {/* <button
        onClick={() => dispatch(setOpenFeatures(!isOpen))}
        className={`flex items-center justify-center h-8 px-2 rounded-full bg-blue-600 text-white
               hover:bg-blue-700 focus:outline-none shadow-lg
               transition-all duration-200 ease-in-out
               ${isOpen ? "ring-2 ring-offset-2 ring-blue-500" : ""}`}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {isOpen ? <X size={24} /> : <Plus size={24} />}
        <span className="text-sm">Tools</span>
      </button> */}
    </div>
  );
};

export default FeatureSelection;
