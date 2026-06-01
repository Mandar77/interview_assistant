/**
 * SchedulerPage - live interview scheduler (Phase 13F).
 * Location: frontend/src/pages/employer/SchedulerPage.tsx
 */

import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { schedulerApi } from "../../api/platform";

export default function SchedulerPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const attemptId = (location.state as any)?.attemptId as string | undefined;

  const [slots, setSlots] = useState<any[]>([]);
  const [username, setUsername] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [provider, setProvider] = useState("meet");
  const [busy, setBusy] = useState(false);

  const load = () => {
    schedulerApi.listSlots().then(setSlots).catch(() => {});
  };
  useEffect(load, []);

  const create = async () => {
    if (!username || !start || !end) {
      alert("Fill candidate, start and end");
      return;
    }
    setBusy(true);
    try {
      await schedulerApi.createSlot({
        candidate_username: username,
        start_time: start,
        end_time: end,
        provider,
        attempt_id: attemptId,
        send_email: true,
      });
      setUsername("");
      setStart("");
      setEnd("");
      load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-6 py-4 flex items-center gap-3">
          <button onClick={() => navigate("/employer")} className="text-gray-500">← Back</button>
          <h1 className="text-lg font-bold text-gray-900">Live Interview Scheduler</h1>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 max-w-3xl grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow p-6 space-y-3">
          <h2 className="font-bold text-gray-900">Schedule a slot</h2>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Candidate username" className="w-full px-3 py-2 border rounded-lg text-sm" />
          <label className="block text-xs text-gray-500">Start</label>
          <input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" />
          <label className="block text-xs text-gray-500">End</label>
          <input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" />
          <select value={provider} onChange={(e) => setProvider(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm">
            <option value="meet">Google Meet</option>
            <option value="zoom">Zoom</option>
            <option value="teams">Teams</option>
          </select>
          <button onClick={create} disabled={busy} className="w-full px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg disabled:opacity-50">
            Create slot + email candidate
          </button>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-bold text-gray-900 mb-3">Upcoming</h2>
          {slots.length === 0 ? (
            <p className="text-sm text-gray-500">No slots scheduled.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {slots.map((s) => (
                <li key={s.id} className="border border-gray-100 rounded-lg p-3">
                  <p className="font-medium text-gray-800">{s.candidate_username}</p>
                  <p className="text-xs text-gray-500">{new Date(s.start_time).toLocaleString()}</p>
                  <a href={s.meeting_link} target="_blank" rel="noreferrer" className="text-xs text-blue-600 break-all">
                    {s.meeting_link}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
