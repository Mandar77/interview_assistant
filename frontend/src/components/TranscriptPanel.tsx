import React from "react";

interface Props {
  transcript: string;
}

export const TranscriptPanel: React.FC<Props> = ({ transcript }) => {
  return (
    <div
      style={{
        border: "1px solid #ddd",
        padding: "12px",
        height: "150px",
        overflowY: "auto",
      }}
    >
      <strong>Transcript</strong>
      <p>{transcript || "Start speaking..."}</p>
    </div>
  );
};
