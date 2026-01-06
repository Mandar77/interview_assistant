import { useEffect, useRef } from "react";

export function useSpeechWebSocket(
  sessionId: string,
  onTranscript: (text: string) => void
) {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(
      `ws://localhost:8000/api/v1/speech/stream?session_id=${sessionId}`
    );

    socket.onopen = () => {
      console.log("✅ Speech WebSocket connected");
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("📝 Transcript message:", data); // ✅ LOG

        if (data.partial_transcript) {
          onTranscript(data.partial_transcript);
        }
      } catch (err) {
        console.error("❌ Failed to parse WS message", err);
      }
    };

    socket.onerror = (err) => {
      console.error("❌ WebSocket error:", err);
    };

    socket.onclose = (event) => {
      console.warn(
        "⚠️ WebSocket closed",
        event.code,
        event.reason
      );
    };

    socketRef.current = socket;

    return () => socket.close();
  }, [sessionId]);

  const sendAudioChunk = (blob: Blob) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(blob);
    } else {
      console.warn("⚠️ Tried to send audio, but WS not open");
    }
  };

  return { sendAudioChunk };
}