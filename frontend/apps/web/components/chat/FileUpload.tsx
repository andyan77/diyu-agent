"use client";

/**
 * File upload with drag-and-drop + progress indicator.
 *
 * Task card: FW2-6
 * - Drag file to input -> upload progress -> complete -> AI processes
 * - 3-step upload protocol (G2-6): request slot -> upload -> confirm
 * - Success rate >= 99%
 */

import { useCallback, useRef, useState, type DragEvent } from "react";

export interface UploadFile {
  id: string;
  name: string;
  size: number;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

interface FileUploadProps {
  onUpload: (file: File) => Promise<string>;
  onComplete?: (fileId: string) => void;
  accept?: string;
  maxSizeMB?: number;
}

export function FileUpload({
  onUpload,
  onComplete,
  accept,
  maxSizeMB = 10,
}: FileUploadProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(
    async (file: File) => {
      const id = crypto.randomUUID();
      const maxBytes = maxSizeMB * 1024 * 1024;

      if (file.size > maxBytes) {
        setFiles((prev) => [
          ...prev,
          {
            id,
            name: file.name,
            size: file.size,
            progress: 0,
            status: "error",
            error: `File exceeds ${maxSizeMB}MB limit`,
          },
        ]);
        return;
      }

      setFiles((prev) => [
        ...prev,
        { id, name: file.name, size: file.size, progress: 0, status: "uploading" },
      ]);

      try {
        const fileId = await onUpload(file);
        setFiles((prev) =>
          prev.map((f) =>
            f.id === id ? { ...f, progress: 100, status: "done" } : f,
          ),
        );
        onComplete?.(fileId);
      } catch (err) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === id
              ? {
                  ...f,
                  status: "error",
                  error: err instanceof Error ? err.message : "Upload failed",
                }
              : f,
          ),
        );
      }
    },
    [onUpload, onComplete, maxSizeMB],
  );

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      const droppedFiles = Array.from(e.dataTransfer.files);
      for (const file of droppedFiles) {
        void processFile(file);
      }
    },
    [processFile],
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleClick = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(e.target.files ?? []);
      for (const file of selected) {
        void processFile(file);
      }
      // Reset input
      if (inputRef.current) inputRef.current.value = "";
    },
    [processFile],
  );

  return (
    <div data-testid="file-upload">
      <div
        data-testid="drop-zone"
        role="button"
        tabIndex={0}
        aria-label="Drop files here or click to upload"
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") handleClick();
        }}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        style={{
          border: `2px dashed ${isDragOver ? "#3b82f6" : "#d1d5db"}`,
          borderRadius: 8,
          padding: "16px",
          textAlign: "center",
          cursor: "pointer",
          background: isDragOver ? "#eff6ff" : "transparent",
          transition: "border-color 0.2s, background 0.2s",
        }}
      >
        <span style={{ color: "#6b7280", fontSize: 13 }}>
          Drop files or click to upload (max {maxSizeMB}MB)
        </span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        onChange={handleInputChange}
        style={{ display: "none" }}
        data-testid="file-input"
      />

      {files.length > 0 && (
        <ul
          data-testid="upload-list"
          style={{ listStyle: "none", margin: "8px 0 0", padding: 0 }}
        >
          {files.map((file) => (
            <li
              key={file.id}
              data-testid={`upload-${file.id}`}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "4px 0",
                fontSize: 12,
              }}
            >
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                {file.name}
              </span>
              <span
                data-testid={`upload-status-${file.id}`}
                style={{
                  marginLeft: 8,
                  color:
                    file.status === "done"
                      ? "#22c55e"
                      : file.status === "error"
                        ? "#ef4444"
                        : "#6b7280",
                }}
              >
                {file.status === "uploading"
                  ? `${file.progress}%`
                  : file.status === "error"
                    ? file.error
                    : file.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
