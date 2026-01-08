import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import InterviewRoom from "./pages/InterviewRoom";
import ResultsDashboard from "./pages/ResultsDashboard";
import AudioTestPage from "./pages/AudioTestPage";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/audio-test" element={<AudioTestPage />} />
        <Route path="/" element={<HomePage />} />
        <Route path="/interview" element={<InterviewRoom />} />
        <Route path="/results" element={<ResultsDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;