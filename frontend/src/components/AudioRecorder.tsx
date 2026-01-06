import React, { useEffect, useRef, useState } from "react";
import { useSpeechWebSocket } from "../hooks/useSpeechWebSocket";

interface Props {
  stream: MediaStream | null;
  sessionId: string;
  onTranscript: (text: string) => void;
}

const AudioRecorder: React.FC<Props> = ({
  stream,
  sessionId,
  onTranscript,
}) => {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const [recording, setRecording] = useState(false);

  const { sendAudioChunk } = useSpeechWebSocket(
    sessionId,
    onTranscript
  );

  useEffect(() => {
    if (!stream) return;

    recorderRef.current = new MediaRecorder(stream, {
      mimeType: "audio/webm",
    });

    recorderRef.current.ondataavailable = (e) => {
      if (e.data.size > 0) {
        sendAudioChunk(e.data);
      }
    };
  }, [stream]);

  const start = () => {
    recorderRef.current?.start(250); // 🔥 real-time chunks
    setRecording(true);
  };

  const stop = () => {
    recorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <button className="w-full py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 transition text-sm font-medium">
  {recording ? "Stop Answer" : "Start Answer"}
</button>
  );
};

export default AudioRecorder;
