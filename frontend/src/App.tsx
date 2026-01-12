/**
 * App.tsx - Main Application with Routes
 * Location: frontend/src/App.tsx
 *  */

import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import InterviewRoom from "./pages/InterviewRoom";
import ResultsDashboard from "./pages/ResultsDashboard";
import AudioTestPage from "./pages/AudioTestPage";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/audio-test" element={<AudioTestPage />} />
        <Route path="/" element={<HomePage />} />
        <Route path="/interview" element={<InterviewRoom />} />
        <Route path="/results" element={<ResultsDashboard />} />
        <Route path="/progress" element={<AnalyticsDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;