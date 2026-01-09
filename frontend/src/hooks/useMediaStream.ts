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
    let mounted = true;

    async function init() {
      try {
        console.log("Requesting camera access...");
        
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user"
          },
          audio: false, // Audio handled separately by AudioRecorder
        });

        if (!mounted) {
          mediaStream.getTracks().forEach(t => t.stop());
          return;
        }

        console.log("Camera access granted!");
        console.log("Video tracks:", mediaStream.getVideoTracks());
        
        currentStream = mediaStream;
        setStream(mediaStream);

        // Set srcObject and wait for video to be ready
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          
          // Force play after a brief delay
          setTimeout(async () => {
            try {
              if (videoRef.current && mounted) {
                await videoRef.current.play();
                console.log("Video playing!");
                setIsReady(true);
              }
            } catch (playErr) {
              console.error("Video play error:", playErr);
            }
          }, 500);
        }
      } catch (err: any) {
        if (!mounted) return;
        
        console.error("Camera access error:", err);
        setError(err.name === "NotAllowedError" 
          ? "Camera permission denied. Please allow camera access."
          : `Camera error: ${err.message}`
        );
      }
    }

    init();

    // Cleanup function
    return () => {
      mounted = false;
      console.log("Cleaning up camera stream...");
      if (currentStream) {
        currentStream.getTracks().forEach((track) => {
          track.stop();
          console.log("Stopped track:", track.kind);
        });
      }
    };
  }, []); // Empty dependency array - only run once

  return { videoRef, stream, error, isReady };
}