import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

interface Props {
  stream: MediaStream | null;
  onTranscript: (text: string) => void;
}

const AudioRecorder: React.FC<Props> = ({ stream, onTranscript }) => {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false);

  useEffect(() => {
    if (!stream) return;

    const recorder = new MediaRecorder(stream, {
      mimeType: "audio/webm",
    });

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      chunksRef.current = [];

      const formData = new FormData();
      formData.append("audio", blob);

      const res = await api.post("/speech/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      onTranscript(res.data.transcription.text);
    };

    mediaRecorderRef.current = recorder;
  }, [stream]);

  const start = () => {
    mediaRecorderRef.current?.start();
    setRecording(true);
  };

  const stop = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <div>
      {!recording ? (
        <button onClick={start}>Start Answer</button>
      ) : (
        <button onClick={stop}>Stop Answer</button>
      )}
    </div>
  );
};

export default AudioRecorder;
