import React, { useEffect, useState } from "react";

export const InterviewTimer: React.FC<{ seconds: number }> = ({ seconds }) => {
  const [time, setTime] = useState(seconds);

  useEffect(() => {
    const id = setInterval(() => {
      setTime((t) => Math.max(0, t - 1));
    }, 1000);

    return () => clearInterval(id);
  }, []);

  return <div>Time Left: {time}s</div>;
};
