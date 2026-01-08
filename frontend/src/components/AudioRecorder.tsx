import { useEffect, useRef, useState } from "react";

interface Props {
  onStart?: () => void;
  onStop?: () => void;
  onAudioChunk?: (blob: Blob) => void;
  autoStop?: boolean;
  disabled?: boolean;
}

export default function AudioRecorder({
  onStart,
  onStop,
  onAudioChunk,
  autoStop,
  disabled,
}: Props) {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isStoppingRef = useRef(false); // Track if we're in the process of stopping

  // Auto-stop when autoStop prop becomes true
  useEffect(() => {
    if (autoStop && recording) {
      stopRecording();
    }
  }, [autoStop]);

  const startRecording = async () => {
    try {
      setError(null);

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000, // Whisper uses 16kHz
        } 
      });
      
      streamRef.current = stream;

      // Create MediaRecorder with WebM format
      const recorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      // Handle each chunk (250ms intervals)
      recorder.ondataavailable = (e) => {
        // Ignore chunks if we're in the process of stopping
        if (e.data.size > 0 && !isStoppingRef.current) {
          // Send chunk to WebSocket
          onAudioChunk?.(e.data);
        }
      };

      recorder.onstop = () => {
        // Cleanup
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setRecording(false);
        
        // Small delay before calling onStop to ensure last chunks are sent
        setTimeout(() => {
          onStop?.();
        }, 300);
      };

      recorder.onerror = (e) => {
        console.error("MediaRecorder error:", e);
        setError("Recording error occurred");
        stopRecording();
      };

      recorderRef.current = recorder;

      // Start recording with 250ms chunks
      recorder.start(250);
      setRecording(true);
      onStart?.();

      console.log("✅ Recording started");
    } catch (err: any) {
      console.error("Failed to start recording:", err);
      setError(err.message || "Failed to access microphone");
    }
  };

  const stopRecording = () => {
    if (recorderRef.current && recording) {
      isStoppingRef.current = true; // Set flag to ignore future chunks
      recorderRef.current.stop();
      console.log("⏹ Recording stopped");
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recorderRef.current && recording) {
        recorderRef.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3">
        <button
          onClick={startRecording}
          disabled={recording || disabled}
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