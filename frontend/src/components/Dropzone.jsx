import { useCallback, useRef, useState } from "react";

/** Drag-and-drop + click-to-browse uploader. Shared by every tool panel. */
export default function Dropzone({ accept, multiple = false, onFiles, hint }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    (fileList) => {
      const files = Array.from(fileList || []);
      if (files.length) onFiles(multiple ? files : [files[0]]);
    },
    [multiple, onFiles]
  );

  return (
    <div
      className={`dropzone ${dragOver ? "dropzone--over" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        hidden
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="dropzone__icon">⬆</div>
      <div className="dropzone__text">
        Drop {multiple ? "files" : "a file"} here, or click to browse
      </div>
      {hint && <div className="dropzone__hint">{hint}</div>}
    </div>
  );
}
