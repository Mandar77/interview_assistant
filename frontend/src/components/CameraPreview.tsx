/**
 * Self-Contained Camera Preview Component
 * Location: frontend/src/components/CameraPreview.tsx
 */

import { useEffect, useRef, useState } from "react";

interface CameraPreviewProps {
  isRecording?: boolean;
  className?: string;
}

export default function CameraPreview({ isRecording = false, className = "" }: CameraPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;

    async function startCamera() {
      try {
        console.log("📹 Starting camera...");
        
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        
        console.log("✅ Camera access granted");
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          console.log("✅ Stream attached to video");
          
          // Wait for video to be ready
          videoRef.current.onloadeddata = () => {
            console.log("✅ Video loaded!");
            setIsReady(true);
          };
        }
      } catch (err: any) {
        console.error("❌ Camera error:", err);
        setError("Camera access denied");
      }
    }

    startCamera();

    return () => {
      console.log("🛑 Stopping camera...");
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <div className={`bg-white rounded-xl shadow-xl p-4 ${className}`}>
      <h3 className="text-lg font-bold mb-3 flex items-center gap-2 text-gray-900">
        📹 Video Feed
      </h3>
      <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden relative">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
          style={{ transform: 'scaleX(-1)' }}
        />
        
        {!isReady && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center text-white">
              <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p className="text-sm font-semibold">Starting camera...</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center text-white p-6">
              <div className="text-5xl mb-3">⚠️</div>
              <p className="text-sm font-semibold">{error}</p>
            </div>
          </div>
        )}
        
        {isRecording && isReady && (
          <div className="absolute top-4 right-4 flex items-center gap-2 bg-red-600 text-white px-3 py-1.5 rounded-full text-sm font-semibold shadow-lg animate-pulse">
            <div className="w-3 h-3 bg-white rounded-full"></div>
            REC
          </div>
        )}

        {isReady && !error && (
          <div className="absolute bottom-4 left-4 flex items-center gap-2 bg-green-600 text-white px-3 py-1.5 rounded-full text-xs font-semibold">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
            Camera Active
          </div>
        )}
      </div>
    </div>
  );
}