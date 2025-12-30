import React, { useEffect, useState } from "react";
import { api } from "../api/client";

export const QuestionPanel: React.FC = () => {
  const [question, setQuestion] = useState<string>("");

  useEffect(() => {
    async function load() {
      const res = await api.post("/questions/generate-single", {
        job_description:
          "Looking for a Python backend engineer with FastAPI and AWS",
        interview_type: "technical",
        difficulty: "medium",
      });

      setQuestion(res.data.question);
    }

    load();
  }, []);

  return (
    <div>
      <strong>Question</strong>
      <p>{question}</p>
    </div>
  );
};
