/**
 * SchedulerPage — live interview scheduler.
 * Location: frontend/src/pages/employer/SchedulerPage.tsx
 */

import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { CalendarClock, Video } from "lucide-react";
import { schedulerApi } from "../../api/platform";
import AppShell from "../../ui/AppShell";
import { Button, Card, EmptyState, Input, Label, Select } from "../../ui";
import { EMPLOYER_NAV } from "./nav";

export default function SchedulerPage() {
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
      alert("Fill candidate, start and end.");
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
    <AppShell nav={EMPLOYER_NAV} title="Scheduler" maxWidth="max-w-4xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-[var(--text)]">Live Interview Scheduler</h1>
      <p className="mb-6 text-sm text-[var(--text-muted)]">Book a live round and auto-email the candidate a meeting link.</p>

      <div className="grid gap-5 md:grid-cols-2">
        <Card elevated>
          <div className="border-b border-[var(--border)] px-5 py-4">
            <h2 className="flex items-center gap-2 text-base font-semibold text-[var(--text)]">
              <CalendarClock size={16} className="text-[var(--accent)]" /> Schedule a slot
            </h2>
          </div>
          <div className="space-y-3 px-5 py-4">
            <div>
              <Label>Candidate username</Label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="alice" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Start</Label>
                <Input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
              </div>
              <div>
                <Label>End</Label>
                <Input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
              </div>
            </div>
            <div>
              <Label>Provider</Label>
              <Select value={provider} onChange={(e) => setProvider(e.target.value)}>
                <option value="meet">Google Meet</option>
                <option value="zoom">Zoom</option>
                <option value="teams">Microsoft Teams</option>
              </Select>
            </div>
            <Button className="w-full" onClick={create} loading={busy}>
              Create slot & email candidate
            </Button>
          </div>
        </Card>

        <div>
          <h2 className="mb-3 text-base font-semibold text-[var(--text)]">Upcoming</h2>
          {slots.length === 0 ? (
            <EmptyState icon={<CalendarClock size={20} />} title="Nothing scheduled" description="Booked slots will show here with their join links." />
          ) : (
            <div className="space-y-2.5">
              {slots.map((s) => (
                <Card key={s.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium text-[var(--text)]">{s.candidate_username}</p>
                      <p className="text-xs text-[var(--text-muted)]">{new Date(s.start_time).toLocaleString()}</p>
                    </div>
                    <a
                      href={s.meeting_link}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex shrink-0 items-center gap-1.5 rounded-[var(--radius-sm)] bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-medium text-[var(--accent)] transition hover:brightness-110"
                    >
                      <Video size={13} /> Join
                    </a>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
