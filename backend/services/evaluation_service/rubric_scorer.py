"""
Rubric Scorer - Independent per-axis evaluation engines
Location: backend/services/evaluation_service/rubric_scorer.py

DESIGN: there is deliberately NO combined / overall / weighted score.

Every axis is scored by its own engine and reported on its own. The previous
design blended nine categories into one weighted number, which meant a fluent,
confident, well-spoken answer scored a pass even when it was technically wrong —
language and delivery points papered over the technical gap. Splitting the
engines makes an off-topic answer read as "Technical 8 / Language 91" instead of
a misleading "2.9/5 overall".

Engines (all independent, all 0-100, never averaged together):
  technical       - correctness of the answer. CRITICAL. Relevance-gated.
  language        - grammar, vocabulary, clarity, conciseness.
  speech_delivery - pace, filler discipline, pause control.
  body_language   - eye contact, posture, gestures.
  time_management - use of the allotted time.

An engine that has no data reports assessed=False and score=None. It never
invents a neutral mid-band score, because a fabricated 60 is indistinguishable
from an earned 60 and quietly inflates the report.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from utils.llm_client import extract_json_object, get_llm_client

logger = logging.getLogger(__name__)


# =============================================================================
# Scale
# =============================================================================

SCALE_MIN = 0
SCALE_MAX = 100

# Ordered high -> low. `_band` returns the first band whose floor is met.
SCORE_BANDS: Sequence[Tuple[int, str]] = (
    (90, "Exceptional"),
    (75, "Strong"),
    (60, "Adequate"),
    (40, "Weak"),
    (0, "Poor"),
)

SCORE_LEVELS = {
    "90-100": "Exceptional - complete, precise, demonstrates mastery",
    "75-89": "Strong - correct and well reasoned, minor gaps",
    "60-74": "Adequate - broadly correct, noticeable gaps",
    "40-59": "Weak - partially correct, significant errors",
    "0-39": "Poor - wrong, or does not address what was asked",
}

# Per-engine bar for "met the bar on this axis". Technical is held higher
# because it is the axis that actually decides whether the answer was right.
ENGINE_PASS_MARKS = {
    "technical": 60,
    "language": 55,
    "speech_delivery": 55,
    "body_language": 55,
    "time_management": 50,
}


def _band(score: Optional[float]) -> str:
    """Human-readable band for a 0-100 score."""
    if score is None:
        return "Not assessed"
    for floor, label in SCORE_BANDS:
        if score >= floor:
            return label
    return "Poor"


def _clamp(value: float, low: float = SCALE_MIN, high: float = SCALE_MAX) -> float:
    return max(low, min(high, value))


def _score_metric(value: Optional[float], default: Optional[float] = None) -> Optional[float]:
    """Read an upstream 0-100 sub-score (analyzers, MediaPipe) defensively."""
    if value is None:
        return default
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return default


def _num(source: Optional[Dict], key: str, default: float) -> float:
    """Read a numeric metric defensively - analyzers may emit None."""
    if not source:
        return default
    value = source.get(key, default)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _piecewise(value: float, points: Sequence[Tuple[float, float]]) -> float:
    """
    Map a raw metric onto 0-100 by linear interpolation between (input, score)
    breakpoints. `points` must be sorted ascending by input. Values outside the
    range clamp to the nearest endpoint's score.
    """
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return y1
            ratio = (value - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return points[-1][1]


# =============================================================================
# Engine catalogue
# =============================================================================

EVALUATION_ENGINES: Dict[str, Dict[str, Any]] = {
    "technical": {
        "name": "Technical Correctness",
        "description": (
            "Is the answer actually right, and does it address the question asked? "
            "Scored only on substance - fluency and delivery are explicitly excluded."
        ),
        "critical": True,
        "source": "llm_evaluation",
        "dimensions": [
            "relevance",
            "technical_correctness",
            "problem_solving",
            "system_design",
            "factual_accuracy",
        ],
    },
    "language": {
        "name": "Language Quality",
        "description": "Grammar, vocabulary, clarity and conciseness of the wording.",
        "critical": False,
        "source": "language_metrics",
        "dimensions": ["grammar_vocabulary", "clarity", "conciseness"],
    },
    "speech_delivery": {
        "name": "Speech Delivery",
        "description": "Speaking pace, filler-word discipline and pause control.",
        "critical": False,
        "source": "speech_metrics",
        "dimensions": ["pacing", "filler_discipline", "pause_control"],
    },
    "body_language": {
        "name": "Body Language",
        "description": "Eye contact, posture and gesture use on camera.",
        "critical": False,
        "source": "body_language_metrics",
        "dimensions": ["eye_contact", "posture", "gestures"],
    },
    "time_management": {
        "name": "Time Management",
        "description": "Use of the time allotted for the question.",
        "critical": False,
        "source": "timing_metrics",
        "dimensions": ["time_utilization"],
    },
}

DIMENSION_NAMES = {
    "relevance": "Relevance to the Question",
    "technical_correctness": "Technical Accuracy",
    "problem_solving": "Problem-Solving Approach",
    "system_design": "System Design Quality",
    "factual_accuracy": "Factual Accuracy",
    "grammar_vocabulary": "Grammar & Vocabulary",
    "clarity": "Clarity",
    "conciseness": "Conciseness",
    "pacing": "Speaking Pace",
    "filler_discipline": "Filler Words",
    "pause_control": "Pause Control",
    "eye_contact": "Eye Contact",
    "posture": "Posture",
    "gestures": "Gestures",
    "time_utilization": "Time Utilization",
}

# Relevance at or above this needs no gating; below it, the technical score is
# scaled down proportionally. An answer that does not address the question
# cannot earn technical credit no matter how well it is expressed.
RELEVANCE_GATE = 70.0

# Answers longer than this are truncated before grading. A spoken interview
# answer runs a few thousand characters; anything past this is a runaway
# transcript. Without a cap it silently overflows the model context (which
# truncates from an arbitrary end) and pushes grading latency past two minutes.
MAX_ANSWER_CHARS = 8000


# =============================================================================
# Result types
# =============================================================================


@dataclass
class DimensionScore:
    """One measured dimension inside an engine."""
    dimension: str
    dimension_name: str
    score: Optional[float]
    feedback: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class EngineScore:
    """Independent rating for one evaluation axis. Never merged with others."""
    engine: str
    engine_name: str
    score: Optional[float]           # 0-100, or None when not assessed
    band: str
    assessed: bool
    critical: bool
    met_bar: Optional[bool]          # vs this engine's own pass mark
    description: str
    feedback: str
    dimensions: List[DimensionScore] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """
    Per-question evaluation.

    There is no overall/weighted score by design - see the module docstring.
    Consumers that want a headline number should show the technical engine,
    which is the axis that reflects whether the answer was correct.
    """
    session_id: str
    question_id: str
    engines: List[EngineScore]
    strengths: List[str]
    weaknesses: List[str]
    scale_min: int = SCALE_MIN
    scale_max: int = SCALE_MAX
    evaluation_available: bool = True
    notes: List[str] = field(default_factory=list)

    def engine(self, engine_id: str) -> Optional[EngineScore]:
        """Look up a single engine's rating by id."""
        for item in self.engines:
            if item.engine == engine_id:
                return item
        return None

    @property
    def scores(self) -> Dict[str, Optional[float]]:
        """Flat {engine_id: score} view. Deliberately not averaged."""
        return {item.engine: item.score for item in self.engines}


# =============================================================================
# Scorer
# =============================================================================


class RubricScorer:
    """
    Run every evaluation engine independently over one answer.

    Each engine owns its own inputs and its own 0-100 output. No engine can
    raise or lower another engine's score, and nothing is averaged across them.
    """

    def __init__(self) -> None:
        self.llm_client = get_llm_client()
        self.engines = EVALUATION_ENGINES
        self.scale_max = SCALE_MAX

    # ---------------------------------------------------------------- public

    def evaluate(
        self,
        session_id: str,
        question_id: str,
        question_text: str,
        answer_text: str,
        speech_metrics: Optional[Dict] = None,
        language_metrics: Optional[Dict] = None,
        body_language_metrics: Optional[Dict] = None,
        timing_metrics: Optional[Dict] = None,
        interview_type: str = "technical",
    ) -> EvaluationResult:
        """
        Evaluate one answer across all engines.

        Returns an EvaluationResult holding one independent 0-100 rating per
        engine. Engines without input data report assessed=False / score=None
        rather than a made-up neutral score.
        """
        logger.info(
            "Evaluating session=%s question=%s type=%s", session_id, question_id, interview_type
        )

        notes: List[str] = []

        technical = self._score_technical(
            question_text=question_text,
            answer_text=answer_text,
            interview_type=interview_type,
            notes=notes,
        )
        language = self._score_language(language_metrics)
        delivery = self._score_speech_delivery(speech_metrics)
        body = self._score_body_language(body_language_metrics)
        timing = self._score_time_management(timing_metrics)

        engines = [technical, language, delivery, body, timing]
        strengths, weaknesses = self._identify_strengths_weaknesses(engines)

        return EvaluationResult(
            session_id=session_id,
            question_id=question_id,
            engines=engines,
            strengths=strengths,
            weaknesses=weaknesses,
            evaluation_available=technical.assessed,
            notes=notes,
        )

    # ------------------------------------------------------- technical engine

    def _score_technical(
        self,
        question_text: str,
        answer_text: str,
        interview_type: str,
        notes: List[str],
    ) -> EngineScore:
        """
        Correctness engine. This is the critical axis.

        Two things keep it honest:
          1. The grader is told in the strongest terms to ignore fluency, and
             that language/delivery are scored by other engines.
          2. A relevance gate is applied in code afterwards, so an off-topic
             answer is scaled down even if the model was charmed by it.
        """
        engine_meta = self.engines["technical"]
        wants_system_design = interview_type == "system_design"

        if not answer_text or not answer_text.strip():
            return EngineScore(
                engine="technical",
                engine_name=engine_meta["name"],
                score=0.0,
                band=_band(0.0),
                assessed=True,
                critical=True,
                met_bar=False,
                description=engine_meta["description"],
                feedback="No answer was provided, so there is nothing correct to credit.",
                dimensions=[],
                evidence=[],
            )

        graded_answer = answer_text
        if len(graded_answer) > MAX_ANSWER_CHARS:
            graded_answer = graded_answer[:MAX_ANSWER_CHARS]
            notes.append(
                f"Answer was truncated to {MAX_ANSWER_CHARS} characters for grading."
            )
            logger.info("Truncated a %d-char answer for grading", len(answer_text))

        llm = self._evaluate_with_llm(
            question_text=question_text,
            answer_text=graded_answer,
            interview_type=interview_type,
            wants_system_design=wants_system_design,
        )

        if llm is None:
            # The grader was unreachable. Report that honestly instead of
            # handing out a passing default, which is what the old code did.
            notes.append(
                "Technical evaluation was unavailable (the grading model could not be reached)."
            )
            return EngineScore(
                engine="technical",
                engine_name=engine_meta["name"],
                score=None,
                band=_band(None),
                assessed=False,
                critical=True,
                met_bar=None,
                description=engine_meta["description"],
                feedback=(
                    "Could not evaluate technical correctness - the grading model was "
                    "unavailable. No score is reported rather than assuming an average one."
                ),
                dimensions=[],
                evidence=[],
            )

        wanted = ["relevance", "technical_correctness", "problem_solving", "factual_accuracy"]
        if wants_system_design:
            wanted.insert(3, "system_design")

        llm = self._normalise_llm_payload(llm)

        dimensions: List[DimensionScore] = []
        raw: Dict[str, float] = {}
        for key in wanted:
            payload = llm.get(key) or {}
            score = self._coerce_score(payload.get("score"))
            if score is None:
                # Missing dimension in the model's JSON - treat as unproven, not
                # as average. Unproven is 0 credit on a correctness axis.
                score = 0.0
                fb = "The grader did not return a score for this dimension."
            else:
                fb = str(payload.get("feedback") or "No specific feedback.")
            raw[key] = score
            dimensions.append(
                DimensionScore(
                    dimension=key,
                    dimension_name=DIMENSION_NAMES[key],
                    score=round(score, 1),
                    feedback=fb,
                    evidence=[str(e) for e in (payload.get("evidence") or [])][:4],
                )
            )

        # Substance blend. Correctness dominates; relevance is a gate, not a term.
        if wants_system_design:
            weights = {
                "technical_correctness": 0.40,
                "problem_solving": 0.20,
                "system_design": 0.25,
                "factual_accuracy": 0.15,
            }
        else:
            weights = {
                "technical_correctness": 0.55,
                "problem_solving": 0.25,
                "factual_accuracy": 0.20,
            }
        blend = sum(raw.get(key, 0.0) * weight for key, weight in weights.items())

        # Relevance gate: full credit at/above the gate, scaled down below it.
        relevance = raw.get("relevance", 0.0)
        gate = 1.0 if relevance >= RELEVANCE_GATE else relevance / RELEVANCE_GATE
        score = _clamp(blend * gate)

        feedback = str(
            (llm.get("technical_correctness") or {}).get("feedback")
            or "Technical evaluation completed."
        )
        if gate < 1.0:
            feedback = (
                f"Relevance to the question scored {relevance:.0f}/100, which caps the "
                f"technical rating regardless of how the answer was expressed. {feedback}"
            )

        evidence = [f"Relevance: {relevance:.0f}/100"]
        summary = llm.get("summary")
        if summary:
            evidence.append(str(summary))

        return EngineScore(
            engine="technical",
            engine_name=engine_meta["name"],
            score=round(score, 1),
            band=_band(score),
            assessed=True,
            critical=True,
            met_bar=score >= ENGINE_PASS_MARKS["technical"],
            description=engine_meta["description"],
            feedback=feedback,
            dimensions=dimensions,
            evidence=evidence,
        )

    def _evaluate_with_llm(
        self,
        question_text: str,
        answer_text: str,
        interview_type: str,
        wants_system_design: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Ask the grader for the technical dimensions.

        Returns None when the model is unreachable or unparseable, so the caller
        can report "not assessed" instead of inventing a score.
        """
        # Prompt design notes (learned the hard way against llama3.2):
        #  - A JSON skeleton containing literal numbers gets copied verbatim, so
        #    the schema is described in prose and no example values are shown.
        #  - A flat object is far more reliable than nested objects on small
        #    local models, which drop or echo whole sub-objects.
        #  - Relevance is framed positively; leading with the failure wording
        #    made the model parrot "does not address the question" for answers
        #    that plainly did.
        system_prompt = """You are a strict technical interview grader.

You grade ONE thing: whether the candidate's answer is technically CORRECT and
actually ANSWERS the question that was asked.

You MUST completely ignore:
- how fluent, eloquent, polished or grammatical the English is
- vocabulary, tone, confidence, or how professional it sounds
- length, or how much effort the answer appears to show
Those are graded by separate engines and must not influence your scores. A
confident, beautifully worded answer that is wrong or off-topic scores near 0.

Every score is an integer from 0 to 100:
  90-100  Correct, complete and precise; demonstrates mastery
  75-89   Correct and well reasoned; minor gaps
  60-74   Broadly correct; noticeable gaps or imprecision
  40-59   Partially correct; significant gaps or errors
  20-39   Mostly wrong; major misconceptions
  0-19    Wrong, or answers a different question entirely

Rules:
- Judge THIS answer on its own merits. Do not reuse numbers or wording from
  these instructions; they are a scale, not an example grade.
- When genuinely uncertain between two bands, choose the lower one.
- Award no credit for plausible-sounding but unverifiable or hand-waved claims.
Return ONLY a single valid JSON object, no markdown and no commentary."""

        design_spec = ""
        if wants_system_design:
            design_spec = (
                "- system_design_score: architecture quality, scalability reasoning and\n"
                "  explicit trade-offs. Use 0-19 if no design reasoning is present.\n"
                "- system_design_note: one sentence justifying that score.\n"
            )

        prompt = f"""Grade this interview answer.

QUESTION (type: {interview_type}):
{question_text}

CANDIDATE'S ANSWER:
{answer_text}

Return a flat JSON object with exactly these keys:

- relevance_score: how much of this answer is actually about what the question
  asked. Use 90-100 when it directly addresses the question's topic, even if the
  content is wrong. Use 0-19 only when it discusses a different subject entirely
  or is generic filler that never engages the question.
- relevance_note: one sentence naming the topic the answer actually discussed.
- correctness_score: are the technical concepts, facts and solution correct?
- correctness_note: one sentence on what is right and what is wrong, specifically.
- correctness_quote: a short direct quote from the answer supporting that score,
  or an empty string if the answer contains nothing quotable.
- problem_solving_score: is the reasoning structured and the method sound?
- problem_solving_note: one sentence justifying that score.
{design_spec}- factual_accuracy_score: are the specific claims accurate and internally
  consistent? Penalise confident claims that are wrong or unverifiable.
- factual_accuracy_note: one sentence justifying that score.
- summary: one sentence on whether the answer was correct.

All *_score values must be integers between 0 and 100 that you chose for THIS
answer."""

        last_error: Optional[str] = None
        for attempt in (1, 2):
            try:
                response = self.llm_client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.2,
                    max_tokens=3072,
                    # Constrain the model to emit syntactically valid JSON rather
                    # than scraping it out of free text.
                    json_mode=True,
                )
            except Exception as exc:
                logger.error("Technical evaluation LLM call failed: %s", exc)
                return None

            parsed = extract_json_object(response)
            if parsed is not None:
                return parsed

            last_error = (response or "")[:200]
            logger.warning(
                "Technical evaluation returned unparseable JSON (attempt %d/2)", attempt
            )

        logger.error("Technical evaluation JSON parse failed. Raw head: %s", last_error)
        return None

    @staticmethod
    def _normalise_llm_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accept the flat grader reply and reshape it into per-dimension dicts.

        Also tolerates the older nested shape, so a model that happens to answer
        with nested objects is not thrown away.
        """
        flat_keys = {
            "relevance": ("relevance_score", "relevance_note", None),
            "technical_correctness": ("correctness_score", "correctness_note", "correctness_quote"),
            "problem_solving": ("problem_solving_score", "problem_solving_note", None),
            "system_design": ("system_design_score", "system_design_note", None),
            "factual_accuracy": ("factual_accuracy_score", "factual_accuracy_note", None),
        }

        out: Dict[str, Any] = {"summary": payload.get("summary")}
        for dimension, (score_key, note_key, quote_key) in flat_keys.items():
            existing = payload.get(dimension)
            if isinstance(existing, dict):
                out[dimension] = existing  # already nested
                continue
            if score_key not in payload:
                continue
            quote = payload.get(quote_key) if quote_key else None
            out[dimension] = {
                "score": payload.get(score_key),
                "feedback": payload.get(note_key) or "No specific feedback.",
                "evidence": [quote] if quote else [],
            }
        return out

    @staticmethod
    def _coerce_score(value: Any) -> Optional[float]:
        """
        Read a 0-100 score from the model, clamping into range.

        Deliberately does NOT try to detect and rescale an old-style 0-5 answer:
        if the model returned 5 meaning "5/100", rescaling would turn the worst
        possible answer into a perfect one. Under-reading a rare mis-scaled
        response is the safe direction for a correctness gate.
        """
        if value is None:
            return None
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        return _clamp(score)

    # -------------------------------------------------------- language engine

    def _score_language(self, language_metrics: Optional[Dict]) -> EngineScore:
        """Language quality only. Cannot affect the technical rating."""
        meta = self.engines["language"]

        if not language_metrics:
            return self._unassessed(
                "language", meta, "No transcript language metrics were captured."
            )

        # SpeechAnalyzer emits these on 0-100.
        grammar = _score_metric(language_metrics.get("grammar_score"), 0.0) or 0.0
        clarity_raw = _score_metric(language_metrics.get("clarity_score"), 0.0) or 0.0
        conciseness = _score_metric(language_metrics.get("conciseness_score"), 0.0) or 0.0

        vocab_level = language_metrics.get("vocabulary_level", "intermediate")
        unique_ratio = _num(language_metrics, "unique_word_ratio", 0.5)
        readability = _num(language_metrics, "readability_flesch", 50.0)
        avg_sentence = _num(language_metrics, "avg_sentence_length", 15.0)

        vocab_bonus = {"basic": 0.0, "intermediate": 6.0, "advanced": 10.0}.get(vocab_level, 0.0)
        grammar_vocab = _clamp(grammar + vocab_bonus)

        # Clarity blends the analyzer's own score with readability and sentence
        # length, both of which have a comfortable middle rather than a maximum.
        readability_score = _piecewise(
            readability, [(0, 20), (30, 55), (50, 80), (70, 100), (90, 80), (100, 65)]
        )
        sentence_score = _piecewise(
            avg_sentence, [(5, 55), (10, 90), (16, 100), (24, 75), (35, 45), (50, 25)]
        )
        clarity = _clamp(clarity_raw * 0.5 + readability_score * 0.3 + sentence_score * 0.2)

        score = _clamp(grammar_vocab * 0.40 + clarity * 0.40 + conciseness * 0.20)

        notes: List[str] = []
        if grammar_vocab >= 75:
            notes.append("Grammar and word choice are strong")
        elif grammar_vocab < 55:
            notes.append("Grammar and word choice need work")
        if clarity >= 75:
            notes.append("explanations read clearly")
        elif clarity < 55:
            notes.append("explanations are hard to follow")
        if conciseness < 55:
            notes.append("answers could be tightened up")

        dimensions = [
            DimensionScore(
                dimension="grammar_vocabulary",
                dimension_name=DIMENSION_NAMES["grammar_vocabulary"],
                score=round(grammar_vocab, 1),
                feedback=f"Vocabulary level: {vocab_level}. Unique-word ratio: {unique_ratio:.2f}.",
                evidence=[f"Grammar: {grammar:.0f}/100", f"Vocabulary: {vocab_level}"],
            ),
            DimensionScore(
                dimension="clarity",
                dimension_name=DIMENSION_NAMES["clarity"],
                score=round(clarity, 1),
                feedback=(
                    f"Readability (Flesch) {readability:.0f}; "
                    f"average sentence length {avg_sentence:.0f} words."
                ),
                evidence=[f"Flesch: {readability:.0f}", f"Avg sentence: {avg_sentence:.0f} words"],
            ),
            DimensionScore(
                dimension="conciseness",
                dimension_name=DIMENSION_NAMES["conciseness"],
                score=round(conciseness, 1),
                feedback="Measured from redundancy and filler phrasing in the transcript.",
                evidence=[],
            ),
        ]

        return EngineScore(
            engine="language",
            engine_name=meta["name"],
            score=round(score, 1),
            band=_band(score),
            assessed=True,
            critical=False,
            met_bar=score >= ENGINE_PASS_MARKS["language"],
            description=meta["description"],
            feedback=". ".join(notes) if notes else "Language quality is adequate.",
            dimensions=dimensions,
            evidence=[f"Unique-word ratio: {unique_ratio:.2f}"],
        )

    # -------------------------------------------------- speech delivery engine

    def _score_speech_delivery(self, speech_metrics: Optional[Dict]) -> EngineScore:
        """Pace, fillers and pauses. Separate from both language and technical."""
        meta = self.engines["speech_delivery"]

        if not speech_metrics:
            return self._unassessed(
                "speech_delivery", meta, "No speech was captured for this answer."
            )

        wpm = _num(speech_metrics, "words_per_minute", 130.0)
        filler_pct = _num(speech_metrics, "filler_word_percentage", 0.0)
        longest_pause = _num(speech_metrics, "longest_pause_ms", 0.0)
        avg_pause = _num(speech_metrics, "avg_pause_duration_ms", 0.0)
        rate_category = speech_metrics.get("speaking_rate_category", "normal")

        # Ideal conversational range is roughly 120-160 wpm.
        pacing = _piecewise(
            wpm, [(60, 25), (90, 60), (120, 100), (160, 100), (190, 65), (230, 30), (300, 10)]
        )
        filler_discipline = _piecewise(
            filler_pct, [(0, 100), (2, 92), (5, 72), (8, 50), (12, 28), (20, 5)]
        )
        pause_control = _piecewise(
            longest_pause, [(0, 100), (1000, 95), (2000, 75), (3000, 55), (5000, 30), (8000, 10)]
        )

        score = _clamp(pacing * 0.40 + filler_discipline * 0.35 + pause_control * 0.25)

        notes: List[str] = []
        if rate_category == "fast" or wpm > 185:
            notes.append("Slow down slightly")
        elif rate_category == "slow" or wpm < 100:
            notes.append("Speak with a little more energy")
        else:
            notes.append("Good speaking pace")
        if filler_pct > 5:
            notes.append(f"reduce filler words ({filler_pct:.1f}% of words)")
        elif filler_pct < 3:
            notes.append("minimal filler words")
        if longest_pause > 3000:
            notes.append(f"trim long pauses (longest {longest_pause / 1000:.1f}s)")

        dimensions = [
            DimensionScore(
                dimension="pacing",
                dimension_name=DIMENSION_NAMES["pacing"],
                score=round(pacing, 1),
                feedback=f"{wpm:.0f} words per minute ({rate_category}). Target is 120-160.",
                evidence=[f"WPM: {wpm:.0f}"],
            ),
            DimensionScore(
                dimension="filler_discipline",
                dimension_name=DIMENSION_NAMES["filler_discipline"],
                score=round(filler_discipline, 1),
                feedback=f"Filler words made up {filler_pct:.1f}% of what was said.",
                evidence=[f"Filler words: {filler_pct:.1f}%"],
            ),
            DimensionScore(
                dimension="pause_control",
                dimension_name=DIMENSION_NAMES["pause_control"],
                score=round(pause_control, 1),
                feedback=(
                    f"Longest pause {longest_pause / 1000:.1f}s; "
                    f"average {avg_pause / 1000:.1f}s."
                ),
                evidence=[f"Longest pause: {longest_pause / 1000:.1f}s"],
            ),
        ]

        return EngineScore(
            engine="speech_delivery",
            engine_name=meta["name"],
            score=round(score, 1),
            band=_band(score),
            assessed=True,
            critical=False,
            met_bar=score >= ENGINE_PASS_MARKS["speech_delivery"],
            description=meta["description"],
            feedback=". ".join(notes),
            dimensions=dimensions,
            evidence=[f"WPM: {wpm:.0f}", f"Fillers: {filler_pct:.1f}%"],
        )

    # --------------------------------------------------- body language engine

    def _score_body_language(self, body_metrics: Optional[Dict]) -> EngineScore:
        """
        Camera signals only, fully independent of the language engine.

        When the camera produced nothing this reports "not assessed". The old
        behaviour handed out a neutral 3.0/5 for an absent camera, which quietly
        propped up the combined score.
        """
        meta = self.engines["body_language"]

        if not body_metrics:
            return self._unassessed(
                "body_language",
                meta,
                "No camera metrics were captured, so body language was not rated.",
            )

        eye_contact = _num(body_metrics, "eye_contact_percentage", 0.0)
        posture_raw = body_metrics.get("posture_score")
        gesture_freq = _num(body_metrics, "gesture_frequency", 0.0)

        # Ideal eye contact sits around 60-80% - staring is as odd as avoiding.
        eye_score = _piecewise(
            eye_contact, [(0, 5), (20, 30), (40, 65), (60, 100), (80, 100), (92, 75), (100, 55)]
        )
        posture = _score_metric(posture_raw, 0.0) or 0.0
        # A few gestures per minute reads as engaged; constant motion distracts.
        gestures = _piecewise(
            gesture_freq, [(0, 35), (1, 70), (3, 100), (6, 85), (10, 55), (16, 25)]
        )

        score = _clamp(eye_score * 0.40 + posture * 0.40 + gestures * 0.20)

        notes: List[str] = []
        notes.append(
            "Good eye contact" if eye_contact >= 60 else "Look at the camera more consistently"
        )
        if posture >= 75:
            notes.append("professional posture")
        elif posture < 55:
            notes.append("work on a steadier, more upright posture")
        if gesture_freq < 0.5:
            notes.append("use a few more hand gestures to look engaged")

        dimensions = [
            DimensionScore(
                dimension="eye_contact",
                dimension_name=DIMENSION_NAMES["eye_contact"],
                score=round(eye_score, 1),
                feedback=f"Looking at the camera {eye_contact:.0f}% of the time. Target is 60-80%.",
                evidence=[f"Eye contact: {eye_contact:.0f}%"],
            ),
            DimensionScore(
                dimension="posture",
                dimension_name=DIMENSION_NAMES["posture"],
                score=round(posture, 1),
                feedback="Derived from shoulder and head stability on camera.",
                evidence=[],
            ),
            DimensionScore(
                dimension="gestures",
                dimension_name=DIMENSION_NAMES["gestures"],
                score=round(gestures, 1),
                feedback=f"{gesture_freq:.1f} gestures per minute.",
                evidence=[f"Gesture rate: {gesture_freq:.1f}/min"],
            ),
        ]

        return EngineScore(
            engine="body_language",
            engine_name=meta["name"],
            score=round(score, 1),
            band=_band(score),
            assessed=True,
            critical=False,
            met_bar=score >= ENGINE_PASS_MARKS["body_language"],
            description=meta["description"],
            feedback=". ".join(notes),
            dimensions=dimensions,
            evidence=[f"Eye contact: {eye_contact:.0f}%"],
        )

    # -------------------------------------------------- time management engine

    def _score_time_management(self, timing_metrics: Optional[Dict]) -> EngineScore:
        """How well the allotted time was used."""
        meta = self.engines["time_management"]

        if not timing_metrics:
            return self._unassessed("time_management", meta, "No timing data was recorded.")

        time_taken = _num(timing_metrics, "time_taken_seconds", 0.0)
        expected = _num(timing_metrics, "expected_time_seconds", 0.0)

        if expected <= 0:
            return self._unassessed(
                "time_management", meta, "No expected duration was set for this question."
            )

        ratio = time_taken / expected
        score = _piecewise(
            ratio, [(0, 5), (0.25, 30), (0.5, 60), (0.8, 100), (1.0, 100), (1.3, 70), (1.8, 35), (2.5, 15)]
        )

        if 0.8 <= ratio <= 1.0:
            feedback = "Used the available time well."
        elif ratio < 0.5:
            feedback = "The answer was much shorter than the time allowed - there was room to go deeper."
        elif ratio < 0.8:
            feedback = "Finished early; there was time for more detail."
        elif ratio <= 1.3:
            feedback = "Slightly over time, but close to the target."
        else:
            feedback = "Ran well over the expected time."

        dimensions = [
            DimensionScore(
                dimension="time_utilization",
                dimension_name=DIMENSION_NAMES["time_utilization"],
                score=round(score, 1),
                feedback=feedback,
                evidence=[
                    f"Took {time_taken:.0f}s of {expected:.0f}s",
                    f"Used {ratio:.0%} of the allotted time",
                ],
            )
        ]

        return EngineScore(
            engine="time_management",
            engine_name=meta["name"],
            score=round(score, 1),
            band=_band(score),
            assessed=True,
            critical=False,
            met_bar=score >= ENGINE_PASS_MARKS["time_management"],
            description=meta["description"],
            feedback=feedback,
            dimensions=dimensions,
            evidence=[f"Used {ratio:.0%} of the allotted time"],
        )

    # --------------------------------------------------------------- helpers

    def _unassessed(self, engine_id: str, meta: Dict[str, Any], reason: str) -> EngineScore:
        """An engine with no input data. Reports no score rather than a guess."""
        return EngineScore(
            engine=engine_id,
            engine_name=meta["name"],
            score=None,
            band=_band(None),
            assessed=False,
            critical=bool(meta.get("critical")),
            met_bar=None,
            description=meta["description"],
            feedback=reason,
            dimensions=[],
            evidence=[],
        )

    def _identify_strengths_weaknesses(
        self, engines: Sequence[EngineScore]
    ) -> Tuple[List[str], List[str]]:
        """
        Per-engine highlights, each labelled with the axis it came from.

        Labelling matters here: "Language Quality: strong" next to "Technical
        Correctness: weak" is the whole point of splitting the engines.
        """
        scored = [e for e in engines if e.assessed and e.score is not None]
        strengths: List[str] = []
        weaknesses: List[str] = []

        for item in sorted(scored, key=lambda e: e.score or 0, reverse=True):
            if (item.score or 0) >= 75:
                strengths.append(f"{item.engine_name} ({item.score:.0f}/100): {item.feedback}")

        for item in sorted(scored, key=lambda e: e.score or 0):
            if (item.score or 0) < 60:
                weaknesses.append(f"{item.engine_name} ({item.score:.0f}/100): {item.feedback}")

        return strengths, weaknesses


# Module-level instance
rubric_scorer = RubricScorer()


def evaluate_response(**kwargs) -> EvaluationResult:
    """Convenience function for evaluation."""
    return rubric_scorer.evaluate(**kwargs)
