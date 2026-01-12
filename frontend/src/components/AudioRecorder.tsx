// frontend/src/components/AudioRecorder.tsx
// FIXED: Added recording state as controlled prop option, fixed useEffect dependencies

import { useEffect, useRef, useState, useCallback } from "react";

interface Props {
  onStart?: () => void;
  onStop?: () => void;
  onAudioChunk?: (blob: Blob) => void;
  autoStop?: boolean;
  disabled?: boolean;
  // NEW: Optional controlled mode - parent controls recording state
  isRecording?: boolean;
}

export default function AudioRecorder({
  onStart,
  onStop,
  onAudioChunk,
  autoStop,
  disabled,
  isRecording: controlledRecording,
}: Props) {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [internalRecording, setInternalRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isStoppingRef = useRef(false);
  const hasStartedRef = useRef(false); // Track if we've started (sync)

  // Use controlled or internal state
  const recording = controlledRecording !== undefined ? controlledRecording : internalRecording;

  // Auto-stop when autoStop prop becomes true AND we're recording
  useEffect(() => {
    if (autoStop && recording && hasStartedRef.current) {
      console.log("⏰ Auto-stopping due to time up");
      stopRecording();
    }
  }, [autoStop, recording]); // Added recording to dependencies

  const startRecording = useCallback(async () => {
    // Prevent double-start
    if (hasStartedRef.current || isStoppingRef.current) {
      console.log("⚠️ Already started or stopping, ignoring start request");
      return;
    }

    try {
      setError(null);
      hasStartedRef.current = true; // Set synchronously FIRST
      isStoppingRef.current = false;

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        } 
      });
      
      streamRef.current = stream;

      // Create MediaRecorder with WebM format
      const recorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      // Handle each chunk (250ms intervals)
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && !isStoppingRef.current) {
          onAudioChunk?.(e.data);
        }
      };

      recorder.onstop = () => {
        // Cleanup
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setInternalRecording(false);
        hasStartedRef.current = false;
        isStoppingRef.current = false;
        
        // Small delay before calling onStop to ensure last chunks are sent
        setTimeout(() => {
          onStop?.();
        }, 300);
      };

      recorder.onerror = (e) => {
        console.error("MediaRecorder error:", e);
        setError("Recording error occurred");
        hasStartedRef.current = false;
        stopRecording();
      };

      recorderRef.current = recorder;

      // Start recording with 250ms chunks
      recorder.start(250);
      setInternalRecording(true);
      
      // Call onStart AFTER everything is set up
      onStart?.();

      console.log("✅ Recording started");
    } catch (err: any) {
      console.error("Failed to start recording:", err);
      setError(err.message || "Failed to access microphone");
      hasStartedRef.current = false;
    }
  }, [onStart, onAudioChunk, onStop]);

  const stopRecording = useCallback(() => {
    if (!hasStartedRef.current) {
      console.log("⚠️ Not started, ignoring stop request");
      return;
    }
    
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      isStoppingRef.current = true;
      recorderRef.current.stop();
      console.log("⏹ Recording stopped");
    } else {
      // Recorder not active but we thought we started - cleanup
      hasStartedRef.current = false;
      setInternalRecording(false);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      hasStartedRef.current = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3">
        <button
          onClick={startRecording}
          disabled={recording || disabled || hasStartedRef.current}
          className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 disabled:transform-none"
        >
          {recording ? "🎤 Recording..." : "▶️ Start Answer"}
        </button>

        <button
          onClick={stopRecording}
          disabled={!recording || disabled}
          className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 disabled:transform-none"
        >
          ⏹️ Stop Answer
        </button>
      </div>

      {recording && (
        <div className="flex items-center justify-center gap-2 p-3 bg-red-50 border-2 border-red-200 rounded-xl">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
          <span className="text-sm font-semibold text-red-900">Recording in progress...</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border-2 border-red-200 rounded-xl">
          <p className="text-sm text-red-900 font-medium">{error}</p>
        </div>
      )}
    </div>
  );
}