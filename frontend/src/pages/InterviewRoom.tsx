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
    <div className="interview-container">
      <InterviewTimer seconds={300} />
      <QuestionPanel />
      <CameraPreview videoRef={videoRef} />

      <AudioRecorder
        stream={stream}
        sessionId={sessionId}
        onTranscript={appendTranscript}
      />

      <TranscriptPanel transcript={transcript} />
    </div>
  );
};

export default InterviewRoom;
