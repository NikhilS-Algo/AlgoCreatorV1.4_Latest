"use client";

import React, { useEffect, useRef } from "react";
import Shepherd from "shepherd.js";
import "shepherd.js/dist/css/shepherd.css";
import "@/styles/tourStyles.css";
import { useAppDispatch } from "@/redux/hooks";
import { setOpenFeatures } from "@/redux/features/loading/openFeaturesSlice";
import { setMainTab } from "@/redux/features/loading/mainTabSlice";
import { setLeftSidebarOpen, setRightSidebarOpen } from "@/redux/features/loading/sidebarsOpenSlice";


export default function ProductTourShepherd() {
  const tourRef = useRef<Shepherd.Tour | null>(null);
  const dispatch = useAppDispatch();


  useEffect(() => {
    tourRef.current = new Shepherd.Tour({
      useModalOverlay: true,
      defaultStepOptions: {
        classes: "shadow-lg bg-white rounded-lg",
        scrollTo: true,
        cancelIcon: {
          enabled: true,
        },
        modalOverlayOpeningPadding: 8, // 8px padding around the focused element
        modalOverlayOpeningRadius: 8, // 8px border radius for the overlay opening
      },
    });

    // Add custom CSS for tooltip spacing
    const style = document.createElement("style");
    style.textContent = `
      .shepherd-modal-overlay-container .shepherd-modal-overlay {
        /* Additional customization for the overlay if needed */
      }
      
      .shepherd-modal-overlay-container .shepherd-modal-overlay .shepherd-modal-mask-rect {
        /* Smooth transition for the overlay opening */
        transition: all 0.3s ease-in-out;
      }

      /* Force 10px spacing between tooltip and target element using CSS transforms */
      .shepherd-element[data-popper-placement="top"] {
        transform: translateY(-10px) !important;
      }

      .shepherd-element[data-popper-placement="bottom"] {
        transform: translateY(10px) !important;
      }

      .shepherd-element[data-popper-placement="left"] {
        transform: translateX(-10px) !important;
      }

      .shepherd-element[data-popper-placement="right"] {
        transform: translateX(10px) !important;
      }

      /* Also add margin as fallback */
      .shepherd-element {
        margin: 10px !important;
      }
    `;
    document.head.appendChild(style);

    return () => {
      if (tourRef.current) {
        tourRef.current.complete();
      }
      document.head.removeChild(style);
    };
  }, []);

  const handleStartTour = () => {
    if (!tourRef.current) return;
    tourRef.current.steps = [];

    tourRef.current.addStep({
      id: "step-1",
      title: "Step 1: Select Date Range",
      text: "To begin, you can select a date range by dragging the handles on the <strong>Timeline slider</strong>.",
      attachTo: {
        element: "#timeline-slider",
        on: "right",
      },
      buttons: [
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      beforeShowPromise: () => {
        return new Promise<void>((resolve) => {
          dispatch(setLeftSidebarOpen(true));
          dispatch(setRightSidebarOpen(false));
          setTimeout(resolve, 100);
        });
      },
      modalOverlayOpeningPadding: 12,
      modalOverlayOpeningRadius: 10,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    tourRef.current.addStep({
      id: "step-2",
      title: "Step 2: Use Calendar",
      text: "Alternatively, click the <strong>Calendar</strong> icon to pick specific start and end dates from a calendar view.",
      attachTo: {
        element: "#calendar-btn",
        on: "right",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      modalOverlayOpeningPadding: 10,
      modalOverlayOpeningRadius: 8,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    tourRef.current.addStep({
      id: "step-3",
      title: "Step 3: Apply Dates",
      text: "After setting the dates, click here to apply the filter to your data source.",
      attachTo: {
        element: "#apply-dates-btn",
        on: "right",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      modalOverlayOpeningPadding: 10,
      modalOverlayOpeningRadius: 8,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    tourRef.current.addStep({
      id: "step-4",
      title: "Step 4: Select Folders",
      text: "Now, let's select a folder. You can select the specific folders from which you want to generate presentations.",
      attachTo: {
        element: "#folder-selection",
        on: "right",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      modalOverlayOpeningPadding: 15,
      modalOverlayOpeningRadius: 12,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    tourRef.current.addStep({
      id: "step-5",
      title: "Step 5: View Dashboard",
      text: "Please click the <strong>Dashboard</strong> tab to view the visualization of the dataset.",
      attachTo: {
        element: "#dashboard-tab",
        on: "bottom",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      modalOverlayOpeningPadding: 8,
      modalOverlayOpeningRadius: 6,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    tourRef.current.addStep({
      id: "step-6",
      title: "Step 6: Folder Chart",
      text: "On the dashboard, you can view the <strong>folder structure visualization</strong>.",
      attachTo: {
        element: "#folder-structure-chart",
        on: "left",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      beforeShowPromise: () => {
        return new Promise<void>((resolve) => {
          dispatch(setMainTab('dashboard'));
          setTimeout(resolve, 100);
        });
      },
      modalOverlayOpeningPadding: 20,
      modalOverlayOpeningRadius: 15,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    // ---------------------- NEW STATS STEPS ----------------------

    tourRef.current.addStep({
      id: "stats-1",
      title: "Total Presentations",
      text: "This shows how many presentations are available in your dataset.",
      attachTo: {
        element: "#stats-card-0",
        on: "bottom",
      },
      beforeShowPromise: () => {
        return new Promise(resolve => {
          dispatch(setMainTab("dashboard"));
          setTimeout(resolve, 120);
        });
      },
      buttons: [
        { text: "Back", classes: "shepherd-button-secondary", action() { return tourRef.current?.back(); } },
        { text: "Next", classes: "shepherd-button-primary", action() { return tourRef.current?.next(); } },
      ],
      modalOverlayOpeningPadding: 12,
    });


    tourRef.current.addStep({
      id: "stats-2",
      title: "Total Slides",
      text: "This shows the number of slides in your selected presentations.",
      attachTo: {
        element: "#stats-card-1",
        on: "bottom",
      },
      beforeShowPromise: () => {
        return new Promise(resolve => {
          dispatch(setMainTab("dashboard"));
          setTimeout(resolve, 120);
        });
      },
      buttons: [
        { text: "Back", classes: "shepherd-button-secondary", action() { return tourRef.current?.back(); } },
        { text: "Next", classes: "shepherd-button-primary", action() { return tourRef.current?.next(); } },
      ],
    });


    tourRef.current.addStep({
      id: "stats-3",
      title: "Folders",
      text: "This counts how many folders contain selected files.",
      attachTo: {
        element: "#stats-card-2",
        on: "bottom",
      },
      beforeShowPromise: () => {
        return new Promise(resolve => {
          dispatch(setMainTab("dashboard"));
          setTimeout(resolve, 120);
        });
      },
      buttons: [
        { text: "Back", classes: "shepherd-button-secondary", action() { return tourRef.current?.back(); } },
        { text: "Next", classes: "shepherd-button-primary", action() { return tourRef.current?.next(); } },
      ],
    });


    tourRef.current.addStep({
      id: "stats-4",
      title: "Unique Tags",
      text: "These are all the topics detected in selected presentations.",
      attachTo: {
        element: "#stats-card-3",
        on: "bottom",
      },
      beforeShowPromise: () => {
        return new Promise(resolve => {
          dispatch(setMainTab("dashboard"));
          setTimeout(resolve, 120);
        });
      },
      buttons: [
        { text: "Back", classes: "shepherd-button-secondary", action() { return tourRef.current?.back(); } },
        { text: "Next", classes: "shepherd-button-primary", action() { return tourRef.current?.next(); } },
      ],
    });

    tourRef.current.addStep({
      id: "sunburst-chart",
      title: "Visual Chart",
      text: "Visual Representation of folders",
      attachTo: {
        element: "#sunburst-chart",
        on: "right",
      },
      beforeShowPromise: () => {
        return new Promise(resolve => {
          dispatch(setMainTab("dashboard"));
          setTimeout(resolve, 120);
        });
      },
      buttons: [
        { text: "Back", classes: "shepherd-button-secondary", action() { return tourRef.current?.back(); } },
        { text: "Next", classes: "shepherd-button-primary", action() { return tourRef.current?.next(); } },
      ],
    });

    tourRef.current.addStep({
      id: "summary - card",
      title: "Summary Chart ",
      text: "Represent and visualize the preentations",
      attachTo: {
        element: "#summary-card",
        on: "bottom",
      },
      beforeShowPromise: () => {
        return new Promise(resolve => {
          dispatch(setMainTab("dashboard"));
          setTimeout(resolve, 120);
        });
      },
      buttons: [
        { text: "Back", classes: "shepherd-button-secondary", action() { return tourRef.current?.back(); } },
        { text: "Next", classes: "shepherd-button-primary", action() { return tourRef.current?.next(); } },
      ],
    });

    tourRef.current.addStep({
      id: "top-tag",
      title: "Top Tags",
      text: "These are the top tags",
      attachTo: {
        element: "#top-tag",
        on: "bottom",
      },
      beforeShowPromise: () => {
        return new Promise(resolve => {
          dispatch(setMainTab("dashboard"));
          setTimeout(resolve, 120);
        });
      },
      buttons: [
        { text: "Back", classes: "shepherd-button-secondary", action() { return tourRef.current?.back(); } },
        { text: "Next", classes: "shepherd-button-primary", action() { return tourRef.current?.next(); } },
      ],
    });

    // ---------------------- END STATS STEPS ----------------------

    tourRef.current.addStep({
      id: "step-7",
      title: "Step 7: Enter a Query",
      text: "Type your specific query for the presentation into the chatbox.",
      attachTo: {
        element: "#chat-input",
        on: "top",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      beforeShowPromise: () => {
        return new Promise<void>((resolve) => {
          dispatch(setMainTab('chat'));
          dispatch(setOpenFeatures(false));
          setTimeout(resolve, 100);
        });
      },
      modalOverlayOpeningPadding: 12,
      modalOverlayOpeningRadius: 10,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    // tourRef.current.addStep({
    //   id: "step-8",
    //   title: "Step 8: Select Features",
    //   text: "You can select the features needed.",
    //   attachTo: {
    //     element: "#chat-features",
    //     on: "top",
    //   },
    //   buttons: [
    //     {
    //       text: "Back",
    //       classes: "shepherd-button-secondary",
    //       action() {
    //         return tourRef.current?.back();
    //       },
    //     },
    //     {
    //       text: "Next",
    //       classes: "shepherd-button-primary",
    //       action() {
    //         return tourRef.current?.next();
    //       },
    //     },
    //   ],
    //   beforeShowPromise: () => {
    //     return new Promise<void>((resolve) => {
    //       dispatch(setOpenFeatures(true));
    //       setTimeout(resolve, 100);
    //     });
    //   },
    //   modalOverlayOpeningPadding: 15,
    //   modalOverlayOpeningRadius: 12,
    //   popperOptions: {
    //     modifiers: [
    //       {
    //         name: "offset",
    //         options: {
    //           offset: [0, 10],
    //         },
    //       },
    //     ],
    //   },
    // });

    tourRef.current.addStep({
      id: "step-8",
      title: "Step 8: Send Request",
      text: "Click the Send button to submit your request to the AI.",
      attachTo: {
        element: "#send-btn",
        on: "left",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      beforeShowPromise: () => {
        return new Promise<void>((resolve) => {
          dispatch(setMainTab("chat"));
          dispatch(setOpenFeatures(false));

          // Wait until #send-btn exists
          const check = setInterval(() => {
            if (document.querySelector("#send-btn")) {
              clearInterval(check);
              resolve();
            }
          }, 60);
        });
      },
      modalOverlayOpeningPadding: 10,
      modalOverlayOpeningRadius: 8,
    });

    tourRef.current.addStep({
      id: "step-9",
      title: "Step 9: Move to Generation Tab",
      text: "Click the Generation tab to begin generating your presentation.",
      attachTo: {
        element: "#generation-tab",
        on: "bottom",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Next",
          classes: "shepherd-button-primary",
          action() {
            return tourRef.current?.next();
          },
        },
      ],
      beforeShowPromise: () => {
        return new Promise<void>((resolve) => {
          dispatch(setMainTab("generate"));

          // Wait until #generation-tab exists
          const check = setInterval(() => {
            if (document.querySelector("#generation-tab")) {
              clearInterval(check);
              resolve();
            }
          }, 60);
        });
      },
      modalOverlayOpeningPadding: 15,
      modalOverlayOpeningRadius: 10,
    });

    tourRef.current.addStep({
      id: "step-10",
      title: "Step 10: View Output",
      text: "Your generated presentations will appear in this section. Keep an eye on it!",
      attachTo: {
        element: "#outputs-panel",
        on: "left",
      },
      buttons: [
        {
          text: "Back",
          classes: "shepherd-button-secondary",
          action() {
            return tourRef.current?.back();
          },
        },
        {
          text: "Finish",
          classes: "shepherd-button-primary",
          action() {
            // dispatch(setRightSidebarOpen(false));
            return tourRef.current?.complete();
          },
        },
      ],
      beforeShowPromise: () => {
        return new Promise<void>((resolve) => {
          dispatch(setRightSidebarOpen(true));
          setTimeout(resolve, 100);
        });
      },
      modalOverlayOpeningPadding: 18,
      modalOverlayOpeningRadius: 14,
      popperOptions: {
        modifiers: [
          {
            name: "offset",
            options: {
              offset: [0, 10],
            },
          },
        ],
      },
    });

    tourRef.current.start();
  };

  return (
    <>
      <button
        onClick={handleStartTour}
        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md transition-colors"
      >
        Tour Guide
      </button>
    </>
  );
}
