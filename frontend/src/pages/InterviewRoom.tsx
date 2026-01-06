import { useMediaStream } from "../hooks/useMediaStream";
import { useInterviewSession } from "../hooks/useInterviewSession";
import CameraPreview from "../components/CameraPreview";
import AudioRecorder from "../components/AudioRecorder";
import TranscriptPanel from "../components/TranscriptPanel";
import InterviewTimer from "../components/InterviewTimer";
import QuestionPanel from "../components/QuestionPanel";

const InterviewRoom = () => {
  const { videoRef, stream, error } = useMediaStream();
  const { sessionId, transcript, appendTranscript } =
    useInterviewSession();

  if (error) return <p>{error}</p>;

  return (
  <div className="min-h-screen flex flex-col">
    {/* Header */}
    <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
      <span className="text-sm text-zinc-400">
        Time Left: 289s
      </span>
      <span className="text-xs px-3 py-1 rounded-full bg-zinc-800">
        Technical Interview
      </span>
    </header>

    {/* Main content */}
    <main className="flex flex-1 gap-6 p-6">
      {/* Left column */}
      <section className="w-1/3 flex flex-col gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <CameraPreview videoRef={videoRef} />
        </div>

        <div>
          <AudioRecorder
            stream={stream}
            sessionId={sessionId}
            onTranscript={appendTranscript}
          />
        </div>
      </section>

      {/* Right column */}
      <section className="w-2/3 flex flex-col gap-4">
        <QuestionPanel />

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 h-64 overflow-y-auto">
          <h2 className="text-sm font-semibold text-zinc-400 mb-2">
            Transcript
          </h2>
          <p className="text-sm leading-relaxed">
            {transcript || "Start speaking..."}
          </p>
        </div>
      </section>
    </main>
  </div>
);

};

export default InterviewRoom;
