import { useState, useRef } from "react";
import { api } from "../api/client";

/**
 * Audio Test Page - Debug audio recording and transcription
 * Location: frontend/src/pages/AudioTestPage.tsx
 * 
 * Use this to test if your microphone and transcription work correctly
 * before running a full interview.
 */

export default function AudioTestPage() {
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      const recorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        chunksRef.current = [];

        // Create audio URL for playback
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);

        // Test transcription
        setLoading(true);
        try {
          const formData = new FormData();
          formData.append("audio", blob, "test.webm");
          formData.append("language", "en");
          formData.append("include_segments", "true");

          const response = await api.post("/speech/transcribe", formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });

          setTranscript(response.data.text);
          console.log("Full transcription result:", response.data);
        } catch (error: any) {
          console.error("Transcription failed:", error);
          alert(`Transcription failed: ${error.response?.data?.detail || error.message}`);
        } finally {
          setLoading(false);
        }

        stream.getTracks().forEach((track) => track.stop());
      };

      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch (error: any) {
      alert(`Failed to access microphone: ${error.message}`);
    }
  };

  const stopRecording = () => {
    if (recorderRef.current && recording) {
      recorderRef.current.stop();
      setRecording(false);
    }
  };

  const clearTest = () => {
    setTranscript("");
    setAudioUrl(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Audio & Transcription Test</h1>
        <p className="text-gray-600 mb-8">
          Test your microphone and Whisper transcription before starting an interview
        </p>

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Recording Test</h2>

          <div className="space-y-4">
            <div className="flex gap-4">
              <button
                onClick={startRecording}
                disabled={recording || loading}
                className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {recording ? "Recording..." : "Start Test Recording"}
              </button>

              <button
                onClick={stopRecording}
                disabled={!recording || loading}
                className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Stop Recording
              </button>

              <button
                onClick={clearTest}
                disabled={!transcript || loading}
                className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clear
              </button>
            </div>

            {recording && (
              <div className="flex items-center gap-3 text-red-600">
                <div className="w-4 h-4 bg-red-500 rounded-full animate-pulse" />
                <span className="font-medium">Recording in progress...</span>
              </div>
            )}

            {loading && (
              <div className="flex items-center gap-3 text-blue-600">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
                <span>Transcribing audio...</span>
              </div>
            )}
          </div>
        </div>

        {audioUrl && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Playback</h2>
            <audio controls src={audioUrl} className="w-full" />
            <p className="text-sm text-gray-600 mt-2">
              Listen to verify your audio is clear and audible
            </p>
          </div>
        )}

        {transcript && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Transcription Result</h2>
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <p className="text-gray-900 whitespace-pre-wrap">{transcript}</p>
            </div>

            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="font-semibold text-blue-900 mb-2">
                Quality Check:
              </h3>
              <ul className="space-y-1 text-sm text-gray-700">
                <li>
                  ✓ Does the transcript match what you said?
                </li>
                <li>
                  ✓ Is the audio clear when you play it back?
                </li>
                <li>
                  ✓ Are there any gibberish words or hallucinations?
                </li>
              </ul>
              <p className="text-sm text-gray-600 mt-3">
                If the transcript doesn't match, try:
                <br />• Speaking closer to the microphone
                <br />• Reducing background noise
                <br />• Checking your microphone settings in system preferences
              </p>
            </div>
          </div>
        )}

        {!transcript && !recording && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="font-semibold text-blue-900 mb-3">
              📋 Test Instructions:
            </h3>
            <ol className="list-decimal list-inside space-y-2 text-gray-700">
              <li>Click "Start Test Recording"</li>
              <li>
                Speak clearly for 10-15 seconds (e.g., introduce yourself, describe
                your day)
              </li>
              <li>Click "Stop Recording"</li>
              <li>Listen to the playback to verify audio quality</li>
              <li>Check if the transcription is accurate</li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}