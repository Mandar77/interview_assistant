/**
 * Media Stream Hook - Fixed for reliable camera access
 * Location: frontend/src/hooks/useMediaStream.ts
 */

import { useEffect, useRef, useState } from "react";

export function useMediaStream() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let currentStream: MediaStream | null = null;

    async function init() {
      try {
        console.log("Requesting camera access...");
        
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user"
          },
          audio: false, // Audio is handled separately by AudioRecorder
        });

        console.log("Camera access granted!", mediaStream.getVideoTracks());
        
        currentStream = mediaStream;
        setStream(mediaStream);

        // Wait for videoRef to be available
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          videoRef.current.onloadedmetadata = () => {
            console.log("Video metadata loaded, playing...");
            videoRef.current?.play().then(() => {
              console.log("Video playing!");
              setIsReady(true);
            }).catch((err) => {
              console.error("Failed to play video:", err);
            });
          };
        }
      } catch (err: any) {
        console.error("Camera access error:", err);
        setError(err.name === "NotAllowedError" 
          ? "Camera permission denied. Please allow camera access in browser settings."
          : "Failed to access camera. Please check your camera is not in use by another application."
        );
      }
    }

    init();

    // Cleanup function
    return () => {
      console.log("Cleaning up camera stream...");
      if (currentStream) {
        currentStream.getTracks().forEach((track) => {
          track.stop();
          console.log("Stopped track:", track.kind);
        });
      }
    };
  }, []); // Empty dependency array - only run once on mount

  return { videoRef, stream, error, isReady };
}