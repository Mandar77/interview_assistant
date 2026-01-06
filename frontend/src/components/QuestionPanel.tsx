import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function QuestionPanel() {
  const [question, setQuestion] = useState<string>("Loading question...");

  useEffect(() => {
    async function loadQuestion() {
      try {
        const payload = {
          job_description:
            "We are hiring a backend software engineer with strong experience in Python, FastAPI, RESTful APIs, cloud platforms such as AWS, and system design fundamentals. The candidate should demonstrate strong problem-solving skills and clear communication.",
          interview_type: "technical",
          difficulty: "medium",
          num_questions: 1,
        };

        const res = await api.post("/questions/generate", payload);

        setQuestion(res.data.questions[0].question);
      } catch (err) {
        console.error("Question load failed", err);
        setQuestion("Unable to load question. Backend not responding.");
      }
    }

    loadQuestion();
  }, []);

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <h2 className="text-sm font-semibold text-zinc-400 mb-2">
        Question
      </h2>
      <p className="text-base leading-relaxed">{question}</p>
    </div>
  );
}
