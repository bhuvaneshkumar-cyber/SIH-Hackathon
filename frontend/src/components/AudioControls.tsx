/**
 * AudioControls — Record button, file upload area, and active-file indicator.
 */

import { useRef, type DragEvent } from "react";
import { SampleClips } from "./SampleClips";

interface AudioControlsProps {
  isRecording: boolean;
  onToggleRecord: () => void;
  onFileSelected: (file: File) => void;
  activeFileName: string | null;
  backendConnected: boolean;
}

export function AudioControls({
  isRecording,
  onToggleRecord,
  onFileSelected,
  activeFileName,
  backendConnected,
}: AudioControlsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) onFileSelected(file);
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add("is-dragover");
  };

  const handleDragLeave = (e: DragEvent) => {
    e.currentTarget.classList.remove("is-dragover");
  };

  return (
    <section className="audio-controls animate-slide-up" id="audio-controls">
      {/* Record button */}
      <div className="audio-controls__buttons">
        <button
          className={`btn btn--record ${isRecording ? "is-recording" : ""}`}
          onClick={onToggleRecord}
          disabled={!backendConnected}
          title={isRecording ? "Stop recording" : "Start recording"}
          id="btn-record"
        >
          {isRecording ? "■" : "●"}
        </button>
      </div>

      {/* Upload drop zone */}
      <div
        className="upload-area"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        id="upload-area"
      >
        <span className="upload-area__icon">📁</span>
        <span>
          Drag & drop an audio file, or <strong>click to browse</strong>
        </span>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFileSelected(file);
          }}
          id="audio-file-input"
        />
      </div>

      {/* Sample clips for demo fallback */}
      <SampleClips onFileSelected={onFileSelected} disabled={!backendConnected || isRecording} />

      {/* Active file indicator */}
      {activeFileName && (
        <div className="audio-info animate-fade-in">
          🎵 {activeFileName}
        </div>
      )}

      {/* Waveform (visible when recording) */}
      {isRecording && (
        <div className="waveform animate-fade-in">
          <div className="waveform__bar" />
          <div className="waveform__bar" />
          <div className="waveform__bar" />
          <div className="waveform__bar" />
          <div className="waveform__bar" />
        </div>
      )}
    </section>
  );
}
