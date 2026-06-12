/**
 * Shared employer navigation config for AppShell.
 * Location: frontend/src/pages/employer/nav.tsx
 */

import { CalendarClock, LayoutDashboard, Sparkles, Users } from "lucide-react";
import type { NavItem } from "../../ui/AppShell";

export const EMPLOYER_NAV: NavItem[] = [
  { label: "Assessments", to: "/employer", icon: <LayoutDashboard size={15} /> },
  { label: "Candidates", to: "/employer/recruiter", icon: <Users size={15} /> },
  { label: "Culture", to: "/employer/culture", icon: <Sparkles size={15} /> },
  { label: "Schedule", to: "/employer/scheduler", icon: <CalendarClock size={15} /> },
];
