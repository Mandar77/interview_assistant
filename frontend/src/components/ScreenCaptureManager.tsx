// frontend/src/components/ScreenCaptureManager.tsx

import { useState, useEffect, useRef, useCallback } from 'react';

interface CaptureData {
  screenshot_id: string;
  timestamp: number;
  base64: string;
}

interface ScreenCaptureManagerProps {
  sessionId: string;
  questionId: string;
  isRecording: boolean;
  captureInterval?: number; // seconds
  onCapture?: (base64: string, method: string) => void;
  enableAutoCapture?: boolean;
}

export default function ScreenCaptureManager({
  sessionId,
  questionId,
  isRecording,
  captureInterval = 10,
  onCapture,
  enableAutoCapture = true,
}: ScreenCaptureManagerProps) {
  const [captures, setCaptures] = useState<CaptureData[]>([]);
  const [isCapturing, setIsCapturing] = useState(false);
  const [lastCaptureTime, setLastCaptureTime] = useState<number>(0);
  const [captureCount, setCaptureCount] = useState(0);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Initialize screen capture stream
  const initializeCapture = useCallback(async () => {
    try {
      console.log('🎥 Requesting screen capture permission...');
      
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: 'always',
        } as MediaTrackConstraints,
        audio: false,
      });

      streamRef.current = stream;

      // Create hidden video element for capturing frames
      if (!videoRef.current) {
        videoRef.current = document.createElement('video');
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }

      console.log('✅ Screen capture initialized');
      return true;

    } catch (error: any) {
      console.error('❌ Screen capture failed:', error);
      if (error.name === 'NotAllowedError') {
        alert('Screen sharing permission denied. Please allow screen sharing to use diagram analysis.');
      }
      return false;
    }
  }, []);

  // Capture a single frame
  const captureFrame = useCallback(async (method: 'auto' | 'manual' = 'auto') => {
    if (!streamRef.current || !videoRef.current || isCapturing) {
      // If no stream, request permission
      if (!streamRef.current) {
        const initialized = await initializeCapture();
        if (!initialized) return null;
        
        // Wait for video to be ready
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }

    if (!videoRef.current) return null;

    setIsCapturing(true);

    try {
      const video = videoRef.current;

      // Wait for video to have data
      if (video.readyState < 2) {
        await new Promise(resolve => {
          video.onloadeddata = resolve;
        });
      }

      // Create canvas and capture frame
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        throw new Error('Could not get canvas context');
      }

      ctx.drawImage(video, 0, 0);

      // Convert to base64
      const dataUrl = canvas.toDataURL('image/png');
      const base64 = dataUrl.split(',')[1];

      const captureData: CaptureData = {
        screenshot_id: `${sessionId}_${questionId}_${Date.now()}`,
        timestamp: Date.now(),
        base64: base64,
      };

      setCaptures(prev => [...prev, captureData]);
      setLastCaptureTime(Date.now());
      setCaptureCount(prev => prev + 1);

      console.log(`📸 Captured ${method} screenshot (${Math.round(base64.length / 1024)}KB)`);

      // Call parent callback
      if (onCapture) {
        onCapture(base64, method);
      }

      return base64;

    } catch (error) {
      console.error('Frame capture failed:', error);
      return null;
    } finally {
      setIsCapturing(false);
    }
  }, [sessionId, questionId, isCapturing, onCapture, initializeCapture]);

  // Auto-capture on interval
  useEffect(() => {
    if (!enableAutoCapture || !isRecording) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Start interval capture
    intervalRef.current = setInterval(() => {
      console.log(`⏰ Auto-capture triggered (interval: ${captureInterval}s)`);
      captureFrame('auto');
    }, captureInterval * 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [enableAutoCapture, isRecording, captureInterval, captureFrame]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const handleManualCapture = async () => {
    await captureFrame('manual');
  };

  const formatTimeSince = (timestamp: number) => {
    if (!timestamp) return 'Never';
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.floor(minutes / 60)}h ago`;
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-bold text-sm text-gray-900">📸 Screen Capture</h4>
        {isRecording && enableAutoCapture && (
          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded">
            Auto-capturing
          </span>
        )}
      </div>

      <div className="space-y-3">
        {/* Manual Capture Button */}
        <button
          onClick={handleManualCapture}
          disabled={isCapturing}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {isCapturing ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              Capturing...
            </>
          ) : (
            <>
              📸 Capture Diagram
            </>
          )}
        </button>

        {/* Capture Stats */}
        <div className="p-3 bg-gray-50 rounded-lg space-y-1 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Captures:</span>
            <span className="font-bold text-gray-900">{captureCount}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Last Capture:</span>
            <span className="font-semibold text-gray-700">{formatTimeSince(lastCaptureTime)}</span>
          </div>
          {enableAutoCapture && isRecording && (
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Next Auto:</span>
              <span className="font-semibold text-blue-600">{captureInterval}s</span>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-xs text-blue-900 font-medium leading-relaxed">
            💡 {enableAutoCapture 
              ? `Drawing automatically captured every ${captureInterval}s while recording. Click "Capture Diagram" for immediate capture.`
              : 'Click "Capture Diagram" to save your design for evaluation.'}
          </p>
        </div>
      </div>
    </div>
  );
}