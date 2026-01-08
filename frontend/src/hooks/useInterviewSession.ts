import { useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";

export interface Question {
  id: string;
  question: string;
  interview_type: string;
  difficulty: string;
  skill_tags: string[];
  expected_duration_mins: number;
  evaluation_criteria?: string[];  // Optional field from backend
  sample_answer_points?: string[];  // Optional field from backend
}

export interface QuestionAnswer {
  question: Question;
  transcript: string;
  startedAt: Date;
  endedAt?: Date;
}

export function useInterviewSession() {
  const [sessionId] = useState(uuidv4());
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  const currentQuestion = questions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === questions.length - 1;

  const loadQuestions = useCallback((loadedQuestions: Question[]) => {
    setQuestions(loadedQuestions);
    setCurrentQuestionIndex(0);
    setAnswers([]);
    setIsComplete(false);
  }, []);

  const startAnswer = useCallback(() => {
    if (!currentQuestion) return;

    const answer: QuestionAnswer = {
      question: currentQuestion,
      transcript: "",
      startedAt: new Date(),
    };

    setAnswers((prev) => [...prev, answer]);
  }, [currentQuestion]);

  const updateCurrentTranscript = useCallback((text: string) => {
    setAnswers((prev) => {
      const updated = [...prev];
      if (updated.length > 0) {
        updated[updated.length - 1].transcript = text;
      }
      return updated;
    });
  }, []);

  const completeCurrentAnswer = useCallback(() => {
    setAnswers((prev) => {
      const updated = [...prev];
      if (updated.length > 0) {
        updated[updated.length - 1].endedAt = new Date();
      }
      return updated;
    });
  }, []);

  const nextQuestion = useCallback(() => {
    if (isLastQuestion) {
      setIsComplete(true);
    } else {
      setCurrentQuestionIndex((prev) => prev + 1);
    }
  }, [isLastQuestion]);

  const previousQuestion = useCallback(() => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex((prev) => prev - 1);
    }
  }, [currentQuestionIndex]);

  return {
    sessionId,
    questions,
    currentQuestion,
    currentQuestionIndex,
    answers,
    isComplete,
    isLastQuestion,
    loadQuestions,
    startAnswer,
    updateCurrentTranscript,
    completeCurrentAnswer,
    nextQuestion,
    previousQuestion,
  };
}