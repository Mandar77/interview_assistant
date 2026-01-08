import { useEffect, useState } from "react";
import { api } from "../api/client";

interface Props {
  onQuestionReady: () => void;
}

export default function QuestionPanel({ onQuestionReady }: Props) {
  const [question, setQuestion] = useState("Loading question...");

  useEffect(() => {
    async function load() {
      const res = await api.post("/questions/generate", {
        job_description:
          "We are hiring a backend software engineer with strong experience in Python, FastAPI, RESTful APIs, cloud platforms such as AWS, and system design fundamentals. The candidate should demonstrate strong problem-solving skills and clear communication.",
        interview_type: "technical",
        difficulty: "medium",
        num_questions: 1,
      });

      setQuestion(res.data.questions[0].question);
      onQuestionReady(); // 🔔 start timer
    }

    load();
  }, []);

  return (
    <div className="border p-4 mt-2">
      <strong>Question</strong>
      <p className="mt-2">{question}</p>
    </div>
  );
}
