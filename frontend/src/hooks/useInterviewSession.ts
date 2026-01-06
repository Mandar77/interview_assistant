import { useState } from "react";
import { v4 as uuidv4 } from "uuid";

export function useInterviewSession() {
  const [sessionId] = useState(uuidv4());
  const [transcript, setTranscript] = useState("");

  const appendTranscript = (text: string) => {
    setTranscript((prev) => (prev ? prev + " " + text : text));
  };

  return {
    sessionId,
    transcript,
    appendTranscript,
  };
}
