"use client"

import type React from "react"
import { useState, useRef , useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Upload, AlertCircle } from "lucide-react"
import { ProgressBar } from "./progress-bar"
import { uploadFilesToBackend, getOutline, generateOutline, generateCustomTemplate, generateDefaultTemplate, getTemplateOptions } from "@/lib/api"
import { useSelector } from "react-redux"
import { selectAuth } from "@/redux/features/auth/authSlice"
interface PresentationFormProps {
  onGenerate: (formData: {
    query: string
    files: File[]
    minSlides: number
    maxSlides: number
    style: string
    content: string
    template: string
    sessionId: string
    dataSourceChoice: string
    presentationId: string | null
    // layout: string // Commented out for future use
  }) => void
  isLoading: boolean
}

const STEPS = ["Files", "Query", "Slide Range", "Style", "Content", "Template", "Review"]

const styleOptions = ["professional", "casual", "modern", "minimal", "corporate", "creative"]
const contentOptions = ["bullet-points", "detailed", "visual-heavy", "narrative", "mixed"]
const templateOptions = ["Template 1", "Template 2"]
// const layoutOptions = ["standard", "widescreen", "compact", "detailed"] // Commented out for future use
const dataSourceOptions = [
  { id: "uploaded_only", label: "Uploaded Files Only", condition: (files: File[]) => files.length > 0 },
  { id: "uploaded_plus_corpus", label: "Uploaded + Corpus", condition: (files: File[]) => files.length > 0 },
  { id: "corpus_only", label: "Corpus Only", condition: () => true },
];


export function PresentationForm({ onGenerate, isLoading }: PresentationFormProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [dataSourceChoice, setDataSourceChoice] = useState("corpus_only");
  const { username } = useSelector(selectAuth);
  const { token } = useSelector(selectAuth)


  // Form states
  const [query, setQuery] = useState("")
  const [files, setFiles] = useState<File[]>([])
  const [minSlides, setMinSlides] = useState(5)
  const [maxSlides, setMaxSlides] = useState(10)
  const [style, setStyle] = useState("professional")
  const [content, setContent] = useState("bullet-points")
  const [template, setTemplate] = useState("blue")
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [outline, setOutline] = useState<any[]>([]);
  const [loadingOutline, setLoadingOutline] = useState(false);
  const [customTemplateFile, setCustomTemplateFile] = useState<File | null>(null);
  const [generatingCustomTemplate, setGeneratingCustomTemplate] = useState(false);
  const [presentationId, setPresentationId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);




  // const [layout, setLayout] = useState("standard") // Commented out for future use

  const fileInputRef = useRef<HTMLInputElement>(null)
  const dragOverRef = useRef(false)

  useEffect(() => {
    const fetchTemplates = async () => {
      if (currentStep === 5) {
        try {
          setLoadingTemplates(true);
          const res = await getTemplateOptions();
          console.log("getting template")
          setTemplates(res.templates || []);
        } catch (err) {
          console.error("❌ Failed to load template options:", err);
        } finally {
          setLoadingTemplates(false);
        }
      }
    };
    fetchTemplates();
  }, [currentStep]);


  // Validation functions
  const isStepValid = (step: number): boolean => {
    switch (step) {
      case 0:
        return dataSourceOptions.some(
          opt => opt.id === dataSourceChoice && opt.condition(files)
        );
      case 1: // Query (moved to second)
        return query.trim().length > 0
      case 2: // Slide Range
        return minSlides > 0 && maxSlides > minSlides
      case 3: // Style
        return style !== ""
      case 4: // Content
        return content !== ""
      case 5: // template
        return template !== ""
      case 6: // Review
        return true
      default:
        return false
    }
  }

  const canProceedToNextStep = (): boolean => {
    return isStepValid(currentStep)
  }

  const handleStepClick = (step: number) => {
    // Allow clicking on completed steps or current step
    if (completedSteps.has(step) || step === currentStep) {
      setCurrentStep(step)
    }
  }

  // const handleNext = () => {
  //   if (isStepValid(currentStep)) {
  //     setCompletedSteps((prev) => new Set(prev).add(currentStep))
  //     if (currentStep < STEPS.length - 1) {
  //       setCurrentStep(currentStep + 1)
  //     }
  //   }
  // }
  const handleNext = async () => {
    console.log("hiiii");
    // See this we can remove 
    // 🧩 Prevent duplicate clicks while async actions are running
    if (uploading || loadingOutline || generatingCustomTemplate) return;

    if (currentStep === 0) {
      // ✅ Case 1: User uploaded files → upload them
      if (files.length > 0) {
        try {
          setUploading(true)
          setUploadProgress(0)
          setUploadSuccess(false)

          await new Promise((r) => setTimeout(r, 50))
          const res = await uploadFilesToBackend(files, (p) => setUploadProgress(p), username || "guest_user");
          console.log("✅ Upload result:", res)
          setSessionId(res.session_id)
          setUploadSuccess(true)
        } catch (err) {
          console.error("❌ Upload failed:", err)
          alert("File upload failed. Please try again.")
          return
        } finally {
          setUploading(false)
        }
      }

      // ✅ Case 2: Either files uploaded successfully or corpus_only chosen
      if (
        files.length === 0 && dataSourceChoice === "corpus_only" ||
        files.length > 0 && dataSourceChoice !== ""
      ) {
        setCompletedSteps((prev) => new Set(prev).add(currentStep))
        setCurrentStep(currentStep + 1)
      } else {
        alert("Please select a valid data source option to continue.")
      }
    } else if (isStepValid(currentStep)) {
      setCompletedSteps((prev) => new Set(prev).add(currentStep));

      // Step 3 (style) -> Step 4 (generate outline)
      if (currentStep === 3) {
        // if (!sessionId) {
        //   alert("Missing session ID. Please upload files first.");
        //   return;
        // }

        setLoadingOutline(true);
        setCurrentStep(4); // move to content preview step

        try {
          console.log("🚀 Generating outline with:", { username, sessionId, query, minSlides, maxSlides, style });

          const result = await generateOutline(username || "guest_user", {
            query,
            mode: dataSourceChoice,
            numSlides: maxSlides,
            presentationStyle: style,
          });


          console.log("✅ Outline generated:", result);

          if (result.status === "success" && Array.isArray(result.slides)) {
            setOutline(result);
            setCompletedSteps((prev) => new Set(prev).add(4));
          } else {
            alert(result.message || "Outline generation did not return valid slide data.");
          }
        } catch (err: any) {
          console.error("❌ Outline generation error:", err);
          alert("Error generating outline: " + err.message);
        } finally {
          setLoadingOutline(false);
        }
      }
      // 🧩 Step 5: Handle template selection (custom or default)
      else if (currentStep === 5) {
        try {
          setGeneratingCustomTemplate(true);

          // Case 1️⃣ — custom template upload
          if (template === "custom_upload" && customTemplateFile) {
            console.log("🚀 Uploading custom template for user:", username);

            const res = await generateCustomTemplate(username || "guest_user", customTemplateFile);
            console.log("✅ Custom template generation result:", res);

            if (res.status === "generated" && res.presentation_id) {
              setPresentationId(res.presentation_id); // 🧩 store generated presentation ID
              setCompletedSteps((prev) => new Set(prev).add(currentStep));
              setCurrentStep(currentStep + 1); // move to next step
            } else {
              alert("Template generation failed. Please try again.");
            }
          }

          // Case 2️⃣ — default template
          else if (template && template !== "custom_upload") {
            console.log("🎨 Generating using default template:", template);

            const res = await generateDefaultTemplate(username || "guest_user", template);
            console.log("✅ Default template generation result:", res);

            if (res.status === "generated" && res.presentation_id) {
              setPresentationId(res.presentation_id);
              setCompletedSteps((prev) => new Set(prev).add(currentStep));
              setCurrentStep(currentStep + 1);
            } else {
              alert("Default template generation failed. Please try again.");
            }
          }

          // No template selected
          else {
            alert("Please select a template before continuing.");
          }
        } catch (err: any) {
          console.error("❌ Template generation error:", err);
          alert("Error generating presentation: " + err.message);
        } finally {
          setGeneratingCustomTemplate(false);
        }
      }
       else if (currentStep < STEPS.length - 1) {
        setCurrentStep(currentStep + 1);
      }
    }

    console.log("username : ", username);
  }


  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    dragOverRef.current = true
  }

  const handleDragLeave = () => {
    dragOverRef.current = false
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    dragOverRef.current = false
    const droppedFiles = Array.from(e.dataTransfer.files)
    const validFiles = droppedFiles.filter((file) =>
      [
        "application/pdf",
        "text/plain",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ].includes(file.type),
    )
    setFiles((prev) => [...prev, ...validFiles])
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    if (selectedFiles.length === 0) return

    // ✅ Merge files (avoid duplicates)
    const newFiles = selectedFiles.filter(
      (file) => !files.some((f) => f.name === file.name)
    )
    setFiles((prev) => [...prev, ...newFiles])

    // Reset input so same file can be added again later if needed
    if (fileInputRef.current) fileInputRef.current.value = ""
  }



  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isStepValid(6)) {
      onGenerate({
        query,
        files,
        minSlides,
        maxSlides,
        style,
        content,
        template,
        sessionId,
        dataSourceChoice,
        presentationId,
      });
    }
  };


  return (
    <div className="w-full h-full px-10 py-8 flex flex-col">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2 text-balance">Create Presentation</h1>
        <p className="text-muted-foreground">Transform your content into professional presentations</p>
      </div>

      <ProgressBar
        currentStep={currentStep}
        totalSteps={STEPS.length}
        steps={STEPS}
        onStepClick={handleStepClick}
        completedSteps={completedSteps}
      />

      {/* Form Steps */}
      <div className="bg-card rounded-lg border border-input p-8 mb-8">
        {/* Step 0: Files - Now First */}
        {currentStep === 0 && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <h2 className="text-2xl font-bold text-foreground mb-2">Upload Supporting Documents</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Add PDFs, documents, or presentations to enhance your content
              </p>
            </div>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${dragOverRef.current
                ? "border-primary bg-secondary"
                : "border-input hover:border-primary/50 bg-secondary/50"
                }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                multiple
                accept=".pdf,.txt,.pptx,.docx"
                className="hidden"
              />
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 bg-background rounded-lg flex items-center justify-center">
                  <Upload className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">Drag and drop your files here</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    or{" "}
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-primary hover:text-primary/80 font-medium"
                    >
                      click to browse
                    </button>
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">Supports PDFs, Text files, PPTX, DOCX</p>
              </div>
            </div>

            {files.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">
                  {files.length} file{files.length !== 1 ? "s" : ""} selected
                </p>
                <div className="flex flex-wrap gap-2">
                  {files.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 bg-background border border-input rounded-lg px-3 py-2"
                    >
                      <span className="text-xs text-primary font-medium truncate max-w-[200px]">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="text-primary hover:text-primary/80"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {/* Empty state warning */}
                  {files.length === 0 && (
                    <div className="flex items-center gap-2 text-xs text-destructive">
                      <AlertCircle className="w-4 h-4" />
                      Please upload at least one file to proceed
                    </div>
                  )}
                  {uploading && (
                    <div className="mt-3">
                      <p className="text-sm text-muted-foreground mb-1">
                        Uploading files... {uploadProgress}%
                      </p>
                      <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${uploadProgress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  {uploadSuccess && (
                    <p className="text-sm text-green-600 mt-2">
                      ✅ Files uploaded successfully! Session ID: {sessionId}
                    </p>
                  )}
                </div>
              </div>
            )}
            {/* Always visible Data Source dropdown */}
            <div className="mt-6">
              <label className="block text-sm font-medium text-foreground mb-2">
                Select Data Source
              </label>
              <select
                value={dataSourceChoice}
                onChange={(e) => setDataSourceChoice(e.target.value)}
                className="w-full border border-input rounded-lg px-3 py-2 bg-background text-sm focus:ring-2 focus:ring-primary"
              >
                {[
                  { id: "uploaded_only", label: "Uploaded Files Only" },
                  { id: "uploaded_plus_corpus", label: "Uploaded + Corpus" },
                  { id: "corpus_only", label: "Corpus Only" },
                ].map((opt) => {
                  const isDisabled =
                    (opt.id === "uploaded_only" || opt.id === "uploaded_plus_corpus") &&
                    files.length === 0;

                  return (
                    <option
                      key={opt.id}
                      value={opt.id}
                      disabled={isDisabled}
                      title={
                        isDisabled
                          ? "Upload at least one file to enable this option"
                          : undefined
                      }
                      className={`${isDisabled ? "text-muted-foreground" : "text-foreground"
                        }`}
                    >
                      {opt.label} {isDisabled ? "(Requires upload)" : ""}
                    </option>
                  );
                })}
              </select>

              {files.length === 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  ⚙️ Only <b>Corpus Only</b> is active. Upload files to unlock other options.
                </p>
              )}
            </div>

          </div>
        )}

        {/* Step 1: Query - Now Second */}
        {currentStep === 1 && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <h2 className="text-2xl font-bold text-foreground mb-2">What's your presentation about?</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Describe your topic, key points, or paste relevant content
              </p>
            </div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your presentation topic or content..."
              className="w-full px-4 py-3 border border-input rounded-lg bg-background text-foreground text-sm placeholder:text-muted-foreground hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              rows={6}
            />
            {!query.trim() && (
              <div className="flex items-center gap-2 text-xs text-destructive">
                <AlertCircle className="w-4 h-4" />
                Please enter your presentation content to proceed
              </div>
            )}
          </div>
        )}

        {/* Step 2: Slide Range */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-fade-in">
            <div>
              <h2 className="text-2xl font-bold text-foreground mb-2">Slide Range</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Set the number of slides for your presentation (5-20 only)
              </p>
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground">Slide Count Range</h3>
              <p className="text-xs text-muted-foreground">
                Set the minimum and maximum number of slides for your presentation.
              </p>

              {/* Dual Range Slider Visualization */}
              <div className="relative pt-6 pb-2">
                <div className="flex items-center gap-2 justify-between relative z-10">
                  <input
                    type="range"
                    min="5"
                    max="20"
                    value={minSlides}
                    onChange={(e) => {
                      const value = Number(e.target.value);
                      if (value < maxSlides) setMinSlides(value);
                    }}
                    className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:size-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                  />

                  <input
                    type="range"
                    min="5"
                    max="20"
                    value={maxSlides}
                    onChange={(e) => {
                      const value = Number(e.target.value);
                      if (value > minSlides) setMaxSlides(value);
                    }}
                    className="absolute w-full h-2 bg-transparent appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:size-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent"
                    style={{ pointerEvents: maxSlides > minSlides ? "auto" : "none" }}
                  />

                </div>
              </div>

              {/* Total Range Display */}
              <p className="text-sm text-muted-foreground">
                Total range: <span className="font-semibold text-foreground">{maxSlides - minSlides + 1}</span> slides
              </p>

              {/* Min and Max Input Fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-foreground block mb-2">Minimum Slides</label>
                  <input
                    type="number"
                    min="5"
                    max={maxSlides - 1}
                    value={minSlides}
                    onChange={(e) => {
                      const value = Number.parseInt(e.target.value)
                      if (value >= 5 && value < maxSlides) setMinSlides(value)
                    }}
                    className="w-full px-3 py-2 border border-input rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground block mb-2">Maximum Slides</label>
                  <input
                    type="number"
                    min={minSlides + 1}
                    max="20"
                    value={maxSlides}
                    onChange={(e) => {
                      const value = Number.parseInt(e.target.value)
                      if (value > minSlides && value <= 20) setMaxSlides(value)
                    }}
                    className="w-full px-3 py-2 border border-input rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Quick Presets</h3>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => { setMinSlides(5); setMaxSlides(10); }}
                  className={`px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all ${minSlides === 5 && maxSlides === 10
                      ? "border-primary bg-secondary text-primary"
                      : "border-input bg-background hover:border-primary/50"
                    }`}
                >
                  Quick (5-10)
                </button>

                <button
                  onClick={() => { setMinSlides(10); setMaxSlides(15); }}
                  className={`px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all ${minSlides === 10 && maxSlides === 15
                      ? "border-primary bg-secondary text-primary"
                      : "border-input bg-background hover:border-primary/50"
                    }`}
                >
                  Standard (10-15)
                </button>

                <button
                  onClick={() => { setMinSlides(12); setMaxSlides(18); }}
                  className={`px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all ${minSlides === 12 && maxSlides === 18
                      ? "border-primary bg-secondary text-primary"
                      : "border-input bg-background hover:border-primary/50"
                    }`}
                >
                  Detailed (12-18)
                </button>

                <button
                  onClick={() => { setMinSlides(15); setMaxSlides(20); }}
                  className={`px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all ${minSlides === 15 && maxSlides === 20
                      ? "border-primary bg-secondary text-primary"
                      : "border-input bg-background hover:border-primary/50"
                    }`}
                >
                  Comprehensive (15-20)
                </button>
              </div>
            </div>

            <div className="bg-secondary border border-input rounded-lg p-4 flex items-start gap-3">
              <span className="text-xl mt-0.5">💡</span>
              <div className="text-sm text-muted-foreground">
                <span className="font-semibold text-foreground">Recommendation: </span>
                Most presentations work best with 12-20 slides. Adjust based on your content complexity and presentation
                duration.
              </div>
            </div>

            {minSlides > 0 && maxSlides > minSlides ? null : (
              <div className="flex items-center gap-2 text-xs text-destructive">
                <AlertCircle className="w-4 h-4" />
                Please set a valid slide range (minimum must be less than maximum)
              </div>
            )}
          </div>
        )}

        {/* Step 3: Style */}
        {currentStep === 3 && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <h2 className="text-2xl font-bold text-foreground mb-2 flex items-center gap-2">
                <span>✨</span> Select Style
              </h2>
              <p className="text-sm text-muted-foreground mb-6">Choose a visual style for your presentation</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {[
                { id: "professional", name: "Professional", icon: "🏢" },
                { id: "casual", name: "Casual", icon: "😊" },
                { id: "modern", name: "Modern", icon: "⚡" },
                { id: "minimal", name: "Minimal", icon: "◯" },
                { id: "corporate", name: "Corporate", icon: "📊" },
                { id: "creative", name: "Creative", icon: "🎨" },
              ].map((option) => (
                <button
                  key={option.id}
                  onClick={() => setStyle(option.id)}
                  className={`p-6 rounded-lg border-2 transition-all text-center ${style === option.id
                    ? "border-primary bg-secondary shadow-lg"
                    : "border-input bg-background hover:border-primary/50"
                    }`}
                >
                  <div className="text-4xl mb-3">{option.icon}</div>
                  <div className="text-sm font-semibold text-foreground">{option.name}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Content */}
        {/* Step 4: Content */}
        {currentStep === 4 && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-2xl font-bold">Slide Content Preview</h2>
            {!loadingOutline && outline  && (
              <div className="p-4 border rounded-lg bg-muted/30">
                <h3 className="font-semibold text-xl mb-2">
                  {outline.presentation_title || "Presentation"}
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  {outline.executive_summary || "No executive summary available."}
                </p>
              </div>
            )}

            {loadingOutline ? (
              <div className="flex items-center gap-2 text-primary">
                <span className="animate-spin">⚙️</span>
                <span>Generating outline...</span>
              </div>
            ) : outline.slides.length > 0 ? (
              <div className="space-y-4">
                  {outline.slides.map((slide: any) => (
                    <div
                      key={slide.slide_number}
                      className="p-4 border border-border rounded-lg hover:border-primary/40 transition-colors"
                    >
                      {/* Flex row: text left, images right */}
                      <div className="flex flex-col md:flex-row gap-4 items-start">
                        {/* 📝 Left: Slide text */}
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg text-foreground">
                            {slide.slide_number}. {slide.slide_title}
                          </h3>
                          <p className="text-sm text-muted-foreground mt-1 whitespace-pre-line leading-relaxed">
                            {slide.content || "No content available"}
                          </p>
                        </div>

                        {/* 🖼️ Right: Slide images */}
                        {slide.images && slide.images.length > 0 && (
                          <div className="w-full md:w-2/5 flex flex-wrap gap-3 justify-end">
                            {slide.images.map((img: any, idx: number) => (
                              <div
                                key={idx}
                                className="w-50 h-50 md:w-52 md:h-36 relative rounded-lg overflow-hidden border border-muted shadow-md"
                              >
                                <img
                                  src={`http://localhost:8082${img.image_url}`}
                                  alt={`Slide ${slide.slide_number} image ${idx + 1}`}
                                  className="w-full h-full object-cover"
                                />
                                {img.caption && (
                                  <p className="text-[10px] text-center mt-1 text-muted-foreground line-clamp-2 px-1">
                                    {img.caption}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No outline data received.</p>
            )}
          </div>
        )}
        {/* Step 5: template */}
        {currentStep === 5 && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <h2 className="text-2xl font-bold text-foreground mb-2">Select Template</h2>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid grid-cols-2 gap-4">
                {[
                  ...templates.map((tpl) => ({
                    id: tpl.id,
                    label: tpl.name,
                    description: tpl.description,
                    imgSrc: `${process.env.NEXT_PUBLIC_API_BASE_URL}${tpl.image_url}`, // ✅ fetch image from backend
                  })),
                  {
                    id: "custom_upload",
                    label: "Upload Custom Template",
                    imgSrc: null,
                  },
                ]
                  .map((opt, index) => {
                  const isSelected = template === opt.id;

                  // Handle upload card separately
                  if (opt.id === "custom_upload") {
                    return (
                      <div
                        key={opt.id}
                        onClick={() => document.getElementById("customTemplateInput")?.click()}
                        className={`relative rounded-xl overflow-hidden border-4 border-dashed flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all duration-200 ${isSelected
                          ? "border-primary bg-secondary shadow-lg scale-[1.03]"
                          : "border-input bg-background hover:border-primary/40 hover:scale-[1.02]"
                          }`}
                      >
                        <Upload className="w-8 h-8 text-primary mb-3" />
                        <span className="text-sm font-medium text-foreground">
                          Upload Custom Template
                        </span>
                        <span className="text-xs text-muted-foreground mt-1">
                          Only .pptx files allowed
                        </span>

                        {/* Hidden File Input */}
                        <input
                          id="customTemplateInput"
                          type="file"
                          accept=".pptx"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (!file) return;
                            if (!file.name.endsWith(".pptx")) {
                              alert("Please upload a PPTX file only.");
                              return;
                            }
                            setCustomTemplateFile(file);
                            setTemplate("custom_upload");
                            console.log("📂 Custom template uploaded:", file.name);
                          }}
                          className="hidden"
                        />

                        {customTemplateFile && (
                          <div className="mt-2 text-xs text-primary">
                            ✅ {customTemplateFile.name}
                          </div>
                        )}
                      </div>
                    );
                  }

                  // Normal template cards
                  return (
                    <button
                      key={opt.id}
                      onClick={() => {
                        setTemplate(opt.id);
                        setCustomTemplateFile(null); // clear any previous upload
                      }}
                      className={`relative rounded-xl overflow-hidden border-4 transition-all duration-200 ${isSelected
                        ? "border-primary shadow-lg scale-[1.03]"
                        : "border-transparent hover:scale-[1.02] hover:border-primary/40"
                        }`}
                    >
                      <img
                        src={opt.imgSrc}
                        alt={opt.label}
                        className="w-full h-40 object-cover rounded-lg"
                      />
                      <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-center text-sm py-1">
                        {opt.label}
                      </div>
                    </button>
                  );
                })}
              </div>

            </div>
          </div>
        )}

        {/* Step 6: Layout - Commented out for future use */}
        {/* {currentStep === 6 && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <h2 className="text-2xl font-bold text-foreground mb-2">Choose Layout</h2>
              <p className="text-sm text-muted-foreground mb-4">Select your slide layout preference</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {layoutOptions.map((option) => (
                <button
                  key={option}
                  onClick={() => setLayout(option)}
                  className={`px-4 py-3 rounded-lg border-2 font-medium transition-all text-sm ${
                    layout === option
                      ? "border-primary bg-secondary text-primary"
                      : "border-input bg-background text-foreground hover:border-primary/50"
                  }`}
                >
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </button>
              ))}
            </div>
          </div>
        )} */}

        {/* Step 6: Review */}
        {currentStep === 6 && (
          <div className="space-y-6 animate-fade-in">
            {/* Title */}
            <h2 className="text-3xl font-semibold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
              Review Your Presentation
            </h2>

            {/* Card */}
            <div className="rounded-2xl border border-blue-200/50 bg-gradient-to-br from-blue-50/80 via-white/60 to-blue-100/60 dark:from-zinc-800/50 dark:via-zinc-900/50 dark:to-zinc-800/50 shadow-lg backdrop-blur-md p-6 space-y-4">
              {[
                { label: "Query", value: query },
                { label: "Data Source", value: dataSourceChoice.replaceAll("_", " ") },
                { label: "Files", value: `${files.length} file(s)` },
                { label: "Slide Range", value: `${minSlides} - ${maxSlides}` },
                { label: "Style", value: style },
                { label: "Content", value: content.replace("-", " ") },
                {
                  label: "Template",
                  value:
                    template === "custom_upload"
                      ? `Custom (${customTemplateFile ? customTemplateFile.name : "Not selected"})`
                      : template,
                },
              ].map((item, i) => (
                <div
                  key={i}
                  className="flex justify-between items-center px-4 py-3 rounded-lg bg-white/40 dark:bg-zinc-900/40 hover:bg-blue-50/40 dark:hover:bg-zinc-800/60 border border-blue-100/40 dark:border-zinc-700/50 transition-colors"
                >
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300 tracking-wide">
                    {item.label}
                  </span>
                  <span className="text-base font-semibold text-blue-700 dark:text-blue-400 text-right">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
            {/* Layout commented out */}
            {/* <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-foreground">Layout</span>
                <span className="text-xs text-accent capitalize">{layout}</span>
              </div> */}
          </div>
        )}

      </div>
      {/* Layout commented out */}
      {/* <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-foreground">Layout</span>
                <span className="text-xs text-accent capitalize">{layout}</span>
              </div> */}
      {/* Navigation Buttons */}
      <div className="flex gap-3 justify-between">
        <Button
          onClick={handleBack}
          disabled={currentStep === 0}
          variant="outline"
          className="px-8 py-2.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed bg-transparent"
          // className="px-8 py-2.5 text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 hover:text-white transition-all duration-200 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed bg-transparent"

        >
          Back
        </Button>

        {currentStep < STEPS.length - 1 ? (
          <Button
            onClick={handleNext}
            disabled={uploading || generatingCustomTemplate || !canProceedToNextStep() || isLoading}
            className="flex-1 items-center px-3 py-2 text-sm font-medium bg-blue-500 border border-blue-600 text-white hover:bg-blue-600 hover:text-white transition-all duration-200 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generatingCustomTemplate ? (
              <div className="text-sm flex items-center gap-2">
                <span className="animate-spin">⚙️</span>
                <span>Generating custom template...</span>
              </div>
            ) : uploading ? (
              <div className="text-lg mr-1">
                <svg
                  className="w-5 h-5 animate-spin text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                  ></path>
                </svg>
                <span className="text-black-100 font-medium">Processing...</span>
              </div>
            ) : (
              "Next"
            )}
          </Button>
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={!isStepValid(6) || isLoading}
            className="flex-1 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Generating..." : "Generate Presentation"}
          </Button>
        )}
      </div>
    </div>
  )
}
