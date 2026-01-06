import React, { useEffect, useRef, useState } from "react";

const ALLOWED_TYPES = [
  "application/zip",
  "application/x-zip-compressed",
];

const UploadZipDropdown: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const uploadedFile = files[0];

    if (!ALLOWED_TYPES.includes(uploadedFile.type)) {
      setError("Only .zip files are supported.");
      setFile(null);
      return;
    }

    setError(null);
    setFile(uploadedFile);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  // 👇 Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <>
      <style>{`
        .wrapper {
          width: 420px;
          margin-left: 600px;
          font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .trigger-btn {
          width: 50%;
          margin-left: 20px;
          padding: 10px 14px;
          border-radius: 8px;
          border: 1px solid #d0d5dd;
          background: #0060c7ff;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s ease, box-shadow 0.2s ease;
        }

        .trigger-btn:hover {
          background: #04376dff;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        .panel {
          width: 50%;
          margin-top: 10px;
          padding: 18px;
          border-radius: 12px;
          border: 2px dashed #d0d5dd;
          background: #ffffff;
          text-align: center;
          animation: fadeSlide 0.2s ease-out;
        }

        .panel:hover {
          border-color: #b692f6;
          background: #fafafa;
        }

        .upload-icon {
          width: 36px;
          height: 36px;
          margin: 0 auto 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 8px;
          background: #f4ebff;
          color: #6941c6;
          font-size: 18px;
        }

        .primary-text {
          font-size: 14px;
          font-weight: 500;
          margin-bottom: 4px;
          color: #667085;
        }

        .secondary-text {
          font-size: 13px;
          color: #667085;
        }

        .browse {
          color: #6941c6;
          cursor: pointer;
          font-weight: 500;
        }

        .browse:hover {
          text-decoration: underline;
        }

        .file-name {
          margin-top: 10px;
          font-size: 13px;
          font-weight: 500;
        }

        .error {
          margin-top: 8px;
          font-size: 12px;
          color: #d92d20;
        }

        @keyframes fadeSlide {
          from {
            opacity: 0;
            transform: translateY(-6px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>

      <div className="wrapper" ref={wrapperRef}>
        <button
          className="trigger-btn"
          onClick={() => setOpen((prev) => !prev)}
        >
          Upload Multiple Files
        </button>

        {open && (
          <div
            className="panel"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            <div className="upload-icon">⬆</div>

            <div className="primary-text">
              Drag and drop your ZIP file here
            </div>

            <div className="secondary-text">
              or{" "}
              <span className="browse" onClick={openFileDialog}>
                click to browse
              </span>
            </div>

            <div className="secondary-text" style={{ marginTop: "6px" }}>
              Supports .zip files only
            </div>

            <input
              ref={fileInputRef}
              type="file"
              hidden
              accept=".zip"
              onChange={(e) => handleFiles(e.target.files)}
            />

            {file && (
              <div className="file-name">
                Selected: {file.name}
              </div>
            )}

            {error && <div className="error">{error}</div>}
          </div>
        )}
      </div>
    </>
  );
};

export default UploadZipDropdown;
