/// <reference types="vite/client" />
import { useEffect, useRef, useState } from "react";

// Use environment variable or fallback to localhost for development
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000/ws";

interface WebSocketMessage {
  type: string;
  partial_transcript?: string;
  question_id?: string;
  final_transcript?: string;
  message?: string;
  [key: string]: unknown;
}

interface UseSpeechWebSocketOptions {
  sessionId: string;
  onTranscript?: (text: string) => void;
  onQuestionStarted?: (questionId: string) => void;
  onQuestionEnded?: (questionId: string, finalTranscript: string) => void;
  onConnected?: () => void;
  onError?: (error: string) => void;
}

export function useSpeechWebSocket({
  sessionId,
  onTranscript,
  onQuestionStarted,
  onQuestionEnded,
  onConnected,
  onError,
}: UseSpeechWebSocketOptions) {
  const socketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentQuestionId, setCurrentQuestionId] = useState<string | null>(null);

  useEffect(() => {
    const wsUrl = `${WS_BASE_URL}/api/v1/speech/stream?session_id=${sessionId}`;
    console.log("Connecting to WebSocket:", wsUrl);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("✅ Speech WebSocket connected");
      setIsConnected(true);
      onConnected?.();
    };

    socket.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        console.log("📝 WS message:", data);

        switch (data.type) {
          case "connected":
            onConnected?.();
            break;

          case "partial_transcript":
            if (data.partial_transcript) {
              onTranscript?.(data.partial_transcript);
            }
            break;

          case "question_started":
            if (data.question_id) {
              setCurrentQuestionId(data.question_id);
              onQuestionStarted?.(data.question_id);
            }
            break;

          case "question_ended":
            if (data.question_id && data.final_transcript) {
              onQuestionEnded?.(data.question_id, data.final_transcript);
            }
            setCurrentQuestionId(null);
            break;

          case "error":
          case "warning":
            onError?.(data.message || "Unknown error");
            break;

          case "pong":
            // Keep-alive response
            break;
        }
      } catch (err) {
        console.error("❌ Failed to parse WS message", err);
      }
    };

    socket.onerror = (err) => {
      console.error("❌ WebSocket error:", err);
      setIsConnected(false);
    };

    socket.onclose = (event) => {
      console.warn("⚠️ WebSocket closed", event.code, event.reason);
      setIsConnected(false);
    };

    socketRef.current = socket;

    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [sessionId, onTranscript, onQuestionStarted, onQuestionEnded, onConnected, onError]);

  // Send audio chunk
  const sendAudioChunk = (blob: Blob) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(blob);
    } else {
      console.warn("⚠️ Tried to send audio, but WS not open");
    }
  };

  // Send control message
  const sendControlMessage = (message: Record<string, unknown>) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  };

  // Start a new question
  const startQuestion = (questionId: string, questionText: string) => {
    sendControlMessage({
      type: "start_question",
      question_id: questionId,
      question_text: questionText,
    });
  };

  // End current question
  const endQuestion = () => {
    sendControlMessage({
      type: "end_question",
    });
  };

  // End entire session
  const endSession = () => {
    sendControlMessage({
      type: "end_session",
    });
  };

  // Ping for keep-alive
  const ping = () => {
    sendControlMessage({
      type: "ping",
    });
  };

  return {
    isConnected,
    currentQuestionId,
    sendAudioChunk,
    startQuestion,
    endQuestion,
    endSession,
    ping,
  };
}