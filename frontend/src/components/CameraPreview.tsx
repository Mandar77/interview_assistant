import { useEffect, useRef } from "react";

export default function CameraPreview() {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    async function init() {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    }
    init();
  }, []);

  return (
    <video
      ref={videoRef}
      autoPlay
      muted
      className="w-full h-48 border"
    />
  );
}
