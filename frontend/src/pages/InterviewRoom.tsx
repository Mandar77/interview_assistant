import React, { useState } from "react";
import { useMediaStream } from "../hooks/useMediaStream";
import CameraPreview from "../components/CameraPreview";
import AudioRecorder from "../components/AudioRecorder";
import { TranscriptPanel } from "../components/TranscriptPanel";
import { InterviewTimer } from "../components/InterviewTimer";
import { QuestionPanel } from "../components/QuestionPanel";


const InterviewRoom: React.FC = () => {
  const { videoRef, stream, error } = useMediaStream();
  const [transcript, setTranscript] = useState("");

  if (error) return <p>{error}</p>;

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      <InterviewTimer seconds={300} />
      <QuestionPanel />
      <CameraPreview videoRef={videoRef} />
      <AudioRecorder stream={stream} onTranscript={setTranscript} />
      <TranscriptPanel transcript={transcript} />
    </div>
  );
};

export default InterviewRoom;
