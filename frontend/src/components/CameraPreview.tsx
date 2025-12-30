import React from "react";

interface Props {
  videoRef: React.RefObject<HTMLVideoElement | null>;
}

const CameraPreview: React.FC<Props> = ({ videoRef }) => {
  return (
    <video
      ref={videoRef}
      autoPlay
      muted
      playsInline
      style={{ width: "300px", border: "1px solid #ccc" }}
    />
  );
};

export default CameraPreview;
