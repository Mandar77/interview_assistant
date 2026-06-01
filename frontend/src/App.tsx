/**
 * App.tsx - Main Application with Routes
 * Location: frontend/src/App.tsx
 *
 * Two surfaces share one app:
 *  - Anonymous mock-interview flow (original, unauthenticated): / /interview /results
 *  - Authenticated hiring platform (Phase 9+): employer + candidate portals
 */

import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";

// Original (anonymous) mock-interview flow
import HomePage from "./pages/HomePage";
import InterviewRoom from "./pages/InterviewRoom";
import ResultsDashboard from "./pages/ResultsDashboard";
import AudioTestPage from "./pages/AudioTestPage";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";

// Platform (Phase 9+)
import AuthPage from "./pages/AuthPage";
import EmployerDashboard from "./pages/employer/EmployerDashboard";
import AssessmentBuilder from "./pages/employer/AssessmentBuilder";
import RecruiterPanel from "./pages/employer/RecruiterPanel";
import CultureScraper from "./pages/employer/CultureScraper";
import SchedulerPage from "./pages/employer/SchedulerPage";
import CandidateWorkspace from "./pages/candidate/CandidateWorkspace";
import AttemptRunner from "./pages/candidate/AttemptRunner";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Anonymous mock-interview flow (unchanged) */}
          <Route path="/" element={<HomePage />} />
          <Route path="/interview" element={<InterviewRoom />} />
          <Route path="/results" element={<ResultsDashboard />} />
          <Route path="/audio-test" element={<AudioTestPage />} />
          <Route path="/progress" element={<AnalyticsDashboard />} />

          {/* Auth */}
          <Route path="/login" element={<AuthPage initialMode="login" />} />
          <Route path="/signup" element={<AuthPage initialMode="signup" />} />

          {/* Employer portal */}
          <Route
            path="/employer"
            element={
              <ProtectedRoute roles={["employer_admin", "employer_member"]}>
                <EmployerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/employer/assessments/:id"
            element={
              <ProtectedRoute roles={["employer_admin", "employer_member"]}>
                <AssessmentBuilder />
              </ProtectedRoute>
            }
          />
          <Route
            path="/employer/recruiter"
            element={
              <ProtectedRoute roles={["employer_admin", "employer_member"]}>
                <RecruiterPanel />
              </ProtectedRoute>
            }
          />
          <Route
            path="/employer/culture"
            element={
              <ProtectedRoute roles={["employer_admin", "employer_member"]}>
                <CultureScraper />
              </ProtectedRoute>
            }
          />
          <Route
            path="/employer/scheduler"
            element={
              <ProtectedRoute roles={["employer_admin", "employer_member"]}>
                <SchedulerPage />
              </ProtectedRoute>
            }
          />

          {/* Candidate workspace */}
          <Route
            path="/workspace"
            element={
              <ProtectedRoute roles={["candidate"]}>
                <CandidateWorkspace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace/attempt/:assignmentId"
            element={
              <ProtectedRoute roles={["candidate"]}>
                <AttemptRunner />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
