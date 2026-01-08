import { useEffect, useState } from "react";

interface Props {
  duration: number;
  running: boolean;
  onTimeUp: () => void;
}

export default function InterviewTimer({
  duration,
  running,
  onTimeUp,
}: Props) {
  const [timeLeft, setTimeLeft] = useState(duration);

  useEffect(() => {
    if (!running) return;

    if (timeLeft <= 0) {
      onTimeUp();
      return;
    }

    const id = setInterval(() => {
      setTimeLeft((t) => t - 1);
    }, 1000);

    return () => clearInterval(id);
  }, [running, timeLeft]);

  return <div>Time Left: {timeLeft}s</div>;
}
