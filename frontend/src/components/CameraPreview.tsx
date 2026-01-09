// frontend/src/components/CameraPreview.tsx

import { useEffect, useRef, useState } from "react";
import { FaceMesh, Results as FaceMeshResults, FACEMESH_TESSELATION } from "@mediapipe/face_mesh";
import { Pose, Results as PoseResults, POSE_CONNECTIONS } from "@mediapipe/pose";
import { drawConnectors, drawLandmarks } from "@mediapipe/drawing_utils";

// ============================================================================
// Types
// ============================================================================

export interface BodyLanguageMetrics {
  eye_contact_percentage: number;
  posture_score: number;
  gesture_frequency: number;
  head_movement_stability: number;
  facial_confidence_signals: {
    smile_detected: boolean;
    nod_count: number;
    nervous_ticks: number;
  };
  timestamp: number;
}

interface CameraPreviewProps {
  isRecording?: boolean;
  onMetricsUpdate?: (metrics: BodyLanguageMetrics) => void;
  enableMediaPipe?: boolean;
  className?: string;
}

// ============================================================================
// Main Component
// ============================================================================

export default function CameraPreview({
  isRecording = false,
  onMetricsUpdate,
  enableMediaPipe = true,
  className = "",
}: CameraPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mediaPipeReady, setMediaPipeReady] = useState(false);

  // Metric tracking refs
  const metricsRef = useRef({
    eyeContactFrames: 0,
    totalFrames: 0,
    previousNoseY: 0,
    nodCount: 0,
    gestureCount: 0,
    lastMetricsUpdate: 0,
  });

  // =========================================================================
  // Camera Initialization
  // =========================================================================

  useEffect(() => {
    let stream: MediaStream | null = null;

    async function startCamera() {
      try {
        console.log("📹 Starting camera...");

        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });

        console.log("✅ Camera access granted");

        if (videoRef.current) {
          videoRef.current.srcObject = stream;

          videoRef.current.onloadeddata = () => {
            console.log("✅ Video loaded!");
            setIsReady(true);
          };
        }
      } catch (err: any) {
        console.error("❌ Camera error:", err);
        setError("Camera access denied");
      }
    }

    startCamera();

    return () => {
      console.log("🛑 Stopping camera...");
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // =========================================================================
  // MediaPipe Initialization
  // =========================================================================

  useEffect(() => {
    if (!isReady || !enableMediaPipe || !videoRef.current || !canvasRef.current) {
      return;
    }

    console.log("🤖 Initializing MediaPipe...");

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d")!;

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    // ✅ Cleanup flag to stop animation loop
    let isCleanedUp = false;

    // Initialize FaceMesh
    const faceMesh = new FaceMesh({
      locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
      },
    });

    faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    // Initialize Pose
    const pose = new Pose({
      locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
      },
    });

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    let faceResults: FaceMeshResults | null = null;
    let poseResults: PoseResults | null = null;

    // FaceMesh results handler
    faceMesh.onResults((results) => {
      faceResults = results;
      drawFaceResults(ctx, canvas, results);
    });

    // Pose results handler
    pose.onResults((results) => {
      poseResults = results;
      drawPoseResults(ctx, canvas, results);

      // Compute and send metrics every 30 frames (~1 second at 30fps)
      if (
        faceResults &&
        poseResults &&
        onMetricsUpdate &&
        metricsRef.current.totalFrames % 30 === 0
      ) {
        const metrics = computeBodyLanguageMetrics(
          faceResults,
          poseResults,
          metricsRef.current
        );
        onMetricsUpdate(metrics);
      }
    });

    // ✅ UPDATED: Processing loop with cleanup check
    let frameCount = 0;
    const processFrame = async () => {
      // ✅ Stop if cleaned up
      if (isCleanedUp) {
        return;
      }

      if (video.readyState === video.HAVE_ENOUGH_DATA) {
        frameCount++;

        // Only process when recording (optimization)
        if (isRecording && frameCount % 2 === 0) {
          // Process every 2nd frame to reduce CPU
          try {
            await faceMesh.send({ image: video });
            await pose.send({ image: video });
          } catch (error) {
            // ✅ Silently handle errors from closed MediaPipe instances
            if (!isCleanedUp) {
              console.error("MediaPipe processing error:", error);
            }
          }
        }
      }
      
      // ✅ Only continue loop if not cleaned up
      if (!isCleanedUp) {
        requestAnimationFrame(processFrame);
      }
    };

    console.log("✅ MediaPipe ready, starting processing loop...");
    setMediaPipeReady(true);
    processFrame();

    return () => {
      console.log("🛑 Stopping MediaPipe...");
      // ✅ Set cleanup flag first to stop animation loop
      isCleanedUp = true;
      
      // ✅ Small delay to ensure processFrame stops
      setTimeout(() => {
        faceMesh.close();
        pose.close();
      }, 100);
    };
    // ✅ REMOVED isRecording from dependencies - MediaPipe stays alive during entire interview
  }, [isReady, enableMediaPipe, onMetricsUpdate]);

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <div className={`bg-white rounded-xl shadow-xl p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold flex items-center gap-2 text-gray-900">
          📹 Video Feed
        </h3>
        {mediaPipeReady && enableMediaPipe && (
          <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-1 rounded">
            🤖 AI Active
          </span>
        )}
      </div>

      <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden relative">
        {/* Video element */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
          style={{ transform: "scaleX(-1)" }}
        />

        {/* Canvas overlay for MediaPipe landmarks */}
        {enableMediaPipe && (
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
            style={{ transform: "scaleX(-1)" }}
          />
        )}

        {/* Loading state */}
        {!isReady && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center text-white">
              <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p className="text-sm font-semibold">Starting camera...</p>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center text-white p-6">
              <div className="text-5xl mb-3">⚠️</div>
              <p className="text-sm font-semibold">{error}</p>
            </div>
          </div>
        )}

        {/* Recording indicator */}
        {isRecording && isReady && (
          <div className="absolute top-4 right-4 flex items-center gap-2 bg-red-600 text-white px-3 py-1.5 rounded-full text-sm font-semibold shadow-lg animate-pulse">
            <div className="w-3 h-3 bg-white rounded-full"></div>
            REC
          </div>
        )}

        {/* Camera active indicator */}
        {isReady && !error && (
          <div className="absolute bottom-4 left-4 flex items-center gap-2 bg-green-600 text-white px-3 py-1.5 rounded-full text-xs font-semibold">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
            Camera Active
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// MediaPipe Drawing Functions
// ============================================================================

function drawFaceResults(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  results: FaceMeshResults
) {
  ctx.save();
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
    const landmarks = results.multiFaceLandmarks[0];

    // Draw face mesh (subtle)
    drawConnectors(ctx, landmarks, FACEMESH_TESSELATION, {
      color: "#00FF00",
      lineWidth: 0.5,
    });

    // Draw key points (eyes, nose, mouth)
    const keyPoints = [
      ...landmarks.slice(33, 42), // Left eye
      ...landmarks.slice(362, 382), // Right eye
      landmarks[1], // Nose tip
      ...landmarks.slice(61, 68), // Mouth
    ];

    drawLandmarks(ctx, keyPoints, {
      color: "#FF0000",
      radius: 2,
    });
  }

  ctx.restore();
}

function drawPoseResults(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  results: PoseResults
) {
  if (results.poseLandmarks) {
    // Draw pose skeleton
    drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS, {
      color: "#00FFFF",
      lineWidth: 2,
    });

    drawLandmarks(ctx, results.poseLandmarks, {
      color: "#FF00FF",
      radius: 3,
    });
  }
}

// ============================================================================
// Metrics Computation Functions
// ============================================================================

function computeBodyLanguageMetrics(
  faceResults: FaceMeshResults,
  poseResults: PoseResults,
  metricsTracker: any
): BodyLanguageMetrics {
  metricsTracker.totalFrames++;

  // Eye contact detection
  const eyeContact = detectEyeContact(faceResults);
  if (eyeContact) {
    metricsTracker.eyeContactFrames++;
  }
  const eyeContactPercentage =
    (metricsTracker.eyeContactFrames / metricsTracker.totalFrames) * 100;

  // Posture analysis
  const postureScore = analyzePosture(poseResults);

  // Head movement (nod detection)
  const headMovement = detectHeadMovement(faceResults, metricsTracker);

  // Gesture frequency
  const gestureDetected = detectGestures(poseResults);
  if (gestureDetected) {
    metricsTracker.gestureCount++;
  }
  const gestureFrequency =
    (metricsTracker.gestureCount / metricsTracker.totalFrames) * 30; // per second at ~30fps

  // Confidence signals
  const smileDetected = detectSmile(faceResults);

  return {
    eye_contact_percentage: Math.round(eyeContactPercentage),
    posture_score: postureScore,
    gesture_frequency: Math.round(gestureFrequency * 10) / 10,
    head_movement_stability: headMovement.stability,
    facial_confidence_signals: {
      smile_detected: smileDetected,
      nod_count: metricsTracker.nodCount,
      nervous_ticks: 0,
    },
    timestamp: Date.now(),
  };
}

// Eye contact detection
function detectEyeContact(results: FaceMeshResults): boolean {
  if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
    return false;
  }

  const landmarks = results.multiFaceLandmarks[0];

  // Get eye landmarks
  const leftIris = landmarks[468];
  const rightIris = landmarks[473];

  // Simple heuristic: eyes looking forward if iris is centered
  const lookingForward =
    Math.abs(leftIris.x - landmarks[33].x) < 0.05 &&
    Math.abs(rightIris.x - landmarks[263].x) < 0.05;

  return lookingForward;
}

// Posture analysis
function analyzePosture(results: PoseResults): number {
  if (!results.poseLandmarks) return 3.0;

  const landmarks = results.poseLandmarks;

  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];
  const nose = landmarks[0];

  // Check shoulder alignment
  const shoulderTilt = Math.abs(leftShoulder.y - rightShoulder.y);

  // Check if shoulders are square to camera
  const shoulderDepth = Math.abs((leftShoulder.z || 0) - (rightShoulder.z || 0));

  // Check head position (should be above shoulders)
  const neckPosture =
    nose.y < (leftShoulder.y + rightShoulder.y) / 2;

  // Score calculation (0-5)
  let score = 5.0;
  if (shoulderTilt > 0.05) score -= 1.0; // Tilted shoulders
  if (shoulderDepth > 0.1) score -= 0.5; // Turned away
  if (!neckPosture) score -= 1.5; // Slouching

  return Math.max(0, Math.min(5, score));
}

// Head movement tracking
function detectHeadMovement(
  results: FaceMeshResults,
  tracker: any
): { stability: number } {
  if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
    return { stability: 1.0 };
  }

  const landmarks = results.multiFaceLandmarks[0];
  const noseTip = landmarks[1];
  const currentY = noseTip.y;

  if (tracker.previousNoseY !== 0) {
    const movement = Math.abs(currentY - tracker.previousNoseY);

    // Detect nod
    if (movement > 0.03) {
      tracker.nodCount++;
    }

    // Stability score
    const stability = Math.max(0, 1 - movement * 20);
    tracker.previousNoseY = currentY;

    return { stability };
  }

  tracker.previousNoseY = currentY;
  return { stability: 1.0 };
}

// Gesture detection
function detectGestures(results: PoseResults): boolean {
  if (!results.poseLandmarks) return false;

  const landmarks = results.poseLandmarks;

  const leftWrist = landmarks[15];
  const rightWrist = landmarks[16];
  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];

  // Gesture if hands are raised above shoulders
  const leftHandRaised = leftWrist.y < leftShoulder.y - 0.1;
  const rightHandRaised = rightWrist.y < rightShoulder.y - 0.1;

  return leftHandRaised || rightHandRaised;
}

// Smile detection
function detectSmile(results: FaceMeshResults): boolean {
  if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
    return false;
  }

  const landmarks = results.multiFaceLandmarks[0];

  // Mouth corners and center
  const leftMouthCorner = landmarks[61];
  const rightMouthCorner = landmarks[291];
  const upperLip = landmarks[13];

  // Mouth width
  const mouthWidth = Math.abs(rightMouthCorner.x - leftMouthCorner.x);

  // Mouth corners lifted
  const mouthLift = (leftMouthCorner.y + rightMouthCorner.y) / 2 < upperLip.y;

  // Simple heuristic
  return mouthWidth > 0.2 && mouthLift;
}