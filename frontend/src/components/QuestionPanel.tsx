import React, { useEffect, useState } from "react";
import { api } from "../api/client";

const QuestionPanel: React.FC = () => {
  const [question, setQuestion] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const res = await api.post("/questions/generate-single", {
          job_description:
            "We are looking for a backend software engineer with strong experience in Python, FastAPI, REST APIs, cloud platforms like AWS, and system design fundamentals. The candidate should demonstrate problem-solving skills and communication ability.",
          interview_type: "technical",
          difficulty: "medium",
        });

        console.log("Question API response:", res.data); // ✅ LOG
        setQuestion(res.data.question);
      } catch (error: any) {
        console.error("❌ Question API failed");

        if (error.response) {
          console.error("Status:", error.response.status);
          console.error("Data:", error.response.data);
        } else {
          console.error("Error:", error.message);
        }

        setQuestion("Failed to load question");
      }
    }

    load();
  }, []);

  return (
    <div>
      <strong>Question</strong>
      <p>{question || "Loading question..."}</p>
    </div>
  );
};

export default QuestionPanel;
