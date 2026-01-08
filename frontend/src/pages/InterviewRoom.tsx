import { useState } from "react";
import InterviewTimer from "../components/InterviewTimer";
import QuestionPanel from "../components/QuestionPanel";
import AudioRecorder from "../components/AudioRecorder";
import CameraPreview from "../components/CameraPreview";

export default function InterviewRoom() {
  const [timerRunning, setTimerRunning] = useState(false);
  const [timeUp, setTimeUp] = useState(false);

  return (
    <div className="p-4">
      <InterviewTimer
        duration={300}
        running={timerRunning}
        onTimeUp={() => setTimeUp(true)}
      />

      <CameraPreview />

      <QuestionPanel
        onQuestionReady={() => setTimerRunning(true)}
      />

      <AudioRecorder
        autoStop={timeUp}
        onStopped={() => setTimerRunning(false)}
      />
    </div>
  );
}
