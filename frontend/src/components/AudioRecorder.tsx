import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

interface Props {
  autoStop: boolean;
  onStopped: () => void;
}

export default function AudioRecorder({ autoStop, onStopped }: Props) {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [recording, setRecording] = useState(false);
  const [attemptUsed, setAttemptUsed] = useState(false);

  useEffect(() => {
    if (autoStop && recording) {
      stopRecording();
    }
  }, [autoStop]);

  const startRecording = async () => {
    if (attemptUsed) return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      chunksRef.current = [];

      const formData = new FormData();
      formData.append("audio", blob, "answer.webm");

      await api.post("/speech/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      onStopped(); // ⏹ stop timer
    };

    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
    setAttemptUsed(true);
  };

  const stopRecording = () => {
    recorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <div className="mt-3 flex gap-2">
      <button
        onClick={startRecording}
        disabled={recording || attemptUsed}
      >
        Start Answer
      </button>

      <button
        onClick={stopRecording}
        disabled={!recording}
      >
        Stop Answer
      </button>
    </div>
  );
}
