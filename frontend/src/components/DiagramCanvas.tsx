// frontend/src/components/DiagramCanvas.tsx

import { useRef } from 'react';

interface DiagramCanvasProps {
  onCapture?: (screenshot: string, method: string) => void;
  autoCapture?: boolean;
  isRecording?: boolean;
}

export default function DiagramCanvas({
  onCapture,
  autoCapture = true,
  isRecording = false,
}: DiagramCanvasProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Excalidraw embed URL
  const excalidrawUrl = "https://excalidraw.com/";

  return (
    <div className="flex flex-col h-full bg-[var(--surface)] rounded-lg overflow-hidden">
      {/* Excalidraw Iframe */}
      <div className="flex-1 relative">
        <iframe
          ref={iframeRef}
          src={excalidrawUrl}
          className="w-full h-full border-0"
          title="Excalidraw Diagram Canvas"
          allow="clipboard-read; clipboard-write"
        />
        
        {/* Overlay instructions */}
        <div className="absolute top-4 left-4 bg-[var(--accent)]/90 text-white px-4 py-2 rounded-lg text-sm max-w-xs backdrop-blur-sm">
          <p className="font-semibold mb-1">💡 Drawing Instructions:</p>
          <ul className="text-xs space-y-1">
            <li>• Draw your system design diagram in Excalidraw</li>
            <li>• Use the tools on the left to add components</li>
            <li>• Click "Capture Diagram" button to save</li>
            {autoCapture && isRecording && <li>• Auto-capture active while recording</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}