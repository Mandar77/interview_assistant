/**
 * AudioTestPage — verify microphone + Whisper transcription before an interview.
 * Location: frontend/src/pages/AudioTestPage.tsx
 */

import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Circle, Mic, Square, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { Button, Card, Spinner } from "../ui";
import { BrandMark } from "../ui/AppShell";
import ThemeToggle from "../theme/ThemeToggle";

export default function AudioTestPage() {
  const navigate = useNavigate();
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 },
      });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      recorder.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        chunksRef.current = [];
        setAudioUrl(URL.createObjectURL(blob));
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
        } catch (error: any) {
          alert(`Transcription failed: ${error.response?.data?.detail || error.message}`);
        } finally {
          setLoading(false);
        }
        stream.getTracks().forEach((t) => t.stop());
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
    <div className="min-h-screen bg-[var(--background)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)] glass">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-5">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate("/")} className="flex items-center gap-1.5 rounded-[var(--radius-sm)] px-2 py-1 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text)]">
              <ArrowLeft size={16} /> Home
            </button>
            <div className="flex items-center gap-2">
              <BrandMark size={22} />
              <span className="text-base font-semibold tracking-tight text-[var(--text)]">Audio Test</span>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-5 px-5 py-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text)]">Microphone & transcription test</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Verify your mic and Whisper transcription before a full interview.</p>
        </div>

        <Card className="px-6 py-5">
          <div className="flex flex-wrap gap-3">
            <Button onClick={startRecording} disabled={recording || loading} leftIcon={<Mic size={16} />}>
              {recording ? "Recording…" : "Start recording"}
            </Button>
            <Button variant="danger" onClick={stopRecording} disabled={!recording || loading} leftIcon={<Square size={15} />}>
              Stop
            </Button>
            <Button variant="ghost" onClick={clearTest} disabled={!transcript || loading} leftIcon={<Trash2 size={15} />}>
              Clear
            </Button>
          </div>

          {recording && (
            <div className="mt-4 flex items-center gap-2.5 text-sm font-medium text-[var(--error)]">
              <Circle size={10} className="animate-pulse fill-current" /> Recording in progress…
            </div>
          )}
          {loading && (
            <div className="mt-4 flex items-center gap-2.5 text-sm text-[var(--text-secondary)]">
              <Spinner size={16} /> Transcribing audio…
            </div>
          )}
        </Card>

        {audioUrl && (
          <Card className="px-6 py-5">
            <h2 className="mb-3 text-base font-semibold text-[var(--text)]">Playback</h2>
            <audio controls src={audioUrl} className="w-full" />
            <p className="mt-2 text-sm text-[var(--text-muted)]">Confirm your audio is clear and audible.</p>
          </Card>
        )}

        {transcript ? (
          <Card className="px-6 py-5">
            <h2 className="mb-3 text-base font-semibold text-[var(--text)]">Transcription</h2>
            <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
              <p className="whitespace-pre-wrap text-sm text-[var(--text)]">{transcript}</p>
            </div>
            <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--accent-soft)] px-4 py-3">
              <h3 className="mb-2 text-sm font-semibold text-[var(--accent)]">Quality check</h3>
              <ul className="space-y-1 text-sm text-[var(--text-secondary)]">
                <li>✓ Does the transcript match what you said?</li>
                <li>✓ Is the playback clear?</li>
                <li>✓ Any gibberish or hallucinated words?</li>
              </ul>
            </div>
          </Card>
        ) : (
          !recording && (
            <Card className="px-6 py-5">
              <h3 className="mb-3 text-base font-semibold text-[var(--text)]">How to test</h3>
              <ol className="list-inside list-decimal space-y-1.5 text-sm text-[var(--text-secondary)]">
                <li>Click <b className="text-[var(--text)]">Start recording</b>.</li>
                <li>Speak clearly for 10–15 seconds.</li>
                <li>Click <b className="text-[var(--text)]">Stop</b>.</li>
                <li>Play back to check audio quality.</li>
                <li>Verify the transcription is accurate.</li>
              </ol>
            </Card>
          )
        )}
      </main>
    </div>
  );
}
