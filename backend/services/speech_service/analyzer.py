"""
Speech Analyzer - Compute speech metrics from transcription
Location: backend/services/speech_service/analyzer.py
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

import spacy
import textstat

logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model not found")
    nlp = None


# Common filler words to detect
FILLER_WORDS = {
    # Classic fillers
    "um", "uh", "er", "ah", "like", "you know", "i mean", "so", "actually",
    "basically", "literally", "right", "okay", "well", "anyway",
    # Hedge words
    "kind of", "sort of", "maybe", "perhaps", "probably", "i think",
    "i guess", "i suppose",
    # Repetition starters
    "and uh", "but um", "so uh", "like uh"
}

# Single word fillers for quick detection
SINGLE_FILLERS = {"um", "uh", "er", "ah", "like", "so", "well", "right", "okay", "actually", "basically", "literally"}


@dataclass
class SpeechMetrics:
    """Container for speech analysis metrics."""
    words_per_minute: float
    total_words: int
    total_duration_seconds: float
    filler_word_count: int
    filler_word_percentage: float
    filler_words_found: List[str]
    pause_count: int
    avg_pause_duration_ms: float
    longest_pause_ms: float
    speaking_rate_category: str  # slow, normal, fast


@dataclass
class LanguageMetrics:
    """Container for language quality metrics."""
    grammar_errors: List[Dict]
    grammar_score: float
    vocabulary_level: str
    unique_word_ratio: float
    avg_sentence_length: float
    readability_flesch: float
    readability_flesch_grade: float
    readability_gunning_fog: float
    clarity_score: float
    conciseness_score: float


class SpeechAnalyzer:
    """Analyze speech patterns and quality from transcription."""
    
    def __init__(self):
        self.nlp = nlp
    
    def analyze_speech(
        self,
        transcription: Dict[str, Any]
    ) -> SpeechMetrics:
        """
        Analyze speech metrics from transcription result.
        
        Args:
            transcription: Output from WhisperTranscriber
            
        Returns:
            SpeechMetrics with computed values
        """
        text = transcription.get("text", "")
        duration = transcription.get("duration_seconds", 1)
        segments = transcription.get("segments", [])
        
        # Word count
        words = text.split()
        total_words = len(words)
        
        # Words per minute
        wpm = (total_words / duration) * 60 if duration > 0 else 0
        
        # Filler word analysis
        filler_count, fillers_found = self._count_fillers(text)
        filler_percentage = (filler_count / total_words * 100) if total_words > 0 else 0
        
        # Pause analysis from segments
        pauses = self._analyze_pauses(segments)
        
        # Speaking rate category
        if wpm < 100:
            rate_category = "slow"
        elif wpm < 150:
            rate_category = "normal"
        else:
            rate_category = "fast"
        
        return SpeechMetrics(
            words_per_minute=round(wpm, 1),
            total_words=total_words,
            total_duration_seconds=round(duration, 2),
            filler_word_count=filler_count,
            filler_word_percentage=round(filler_percentage, 2),
            filler_words_found=fillers_found,
            pause_count=pauses["count"],
            avg_pause_duration_ms=round(pauses["avg_ms"], 0),
            longest_pause_ms=round(pauses["max_ms"], 0),
            speaking_rate_category=rate_category
        )
    
    def analyze_language(self, text: str) -> LanguageMetrics:
        """
        Analyze language quality of the transcript.
        
        Args:
            text: Transcribed text
            
        Returns:
            LanguageMetrics with quality scores
        """
        if not text.strip():
            return self._empty_language_metrics()
        
        # Grammar analysis
        grammar_errors = self._check_grammar(text)
        grammar_score = self._calculate_grammar_score(grammar_errors, text)
        
        # Vocabulary analysis
        vocab_level, unique_ratio = self._analyze_vocabulary(text)
        
        # Sentence analysis
        avg_sentence_length = self._avg_sentence_length(text)
        
        # Readability scores
        flesch = textstat.flesch_reading_ease(text)
        flesch_grade = textstat.flesch_kincaid_grade(text)
        gunning_fog = textstat.gunning_fog(text)
        
        # Clarity and conciseness
        clarity_score = self._calculate_clarity_score(text, grammar_errors, flesch)
        conciseness_score = self._calculate_conciseness_score(text)
        
        return LanguageMetrics(
            grammar_errors=grammar_errors[:10],  # Limit to top 10
            grammar_score=round(grammar_score, 2),
            vocabulary_level=vocab_level,
            unique_word_ratio=round(unique_ratio, 2),
            avg_sentence_length=round(avg_sentence_length, 1),
            readability_flesch=round(flesch, 1),
            readability_flesch_grade=round(flesch_grade, 1),
            readability_gunning_fog=round(gunning_fog, 1),
            clarity_score=round(clarity_score, 2),
            conciseness_score=round(conciseness_score, 2)
        )
    
    def _count_fillers(self, text: str) -> Tuple[int, List[str]]:
        """Count filler words in text."""
        text_lower = text.lower()
        words = text_lower.split()
        
        fillers_found = []
        count = 0
        
        # Count single-word fillers
        for word in words:
            # Clean punctuation
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in SINGLE_FILLERS:
                count += 1
                fillers_found.append(clean_word)
        
        # Count multi-word fillers
        for filler in FILLER_WORDS:
            if ' ' in filler:  # Multi-word
                occurrences = text_lower.count(filler)
                if occurrences > 0:
                    count += occurrences
                    fillers_found.extend([filler] * occurrences)
        
        # Get top fillers with counts
        filler_counts = Counter(fillers_found)
        top_fillers = [f"{word} ({cnt})" for word, cnt in filler_counts.most_common(5)]
        
        return count, top_fillers
    
    def _analyze_pauses(self, segments: List[Dict]) -> Dict[str, float]:
        """Analyze pauses between speech segments."""
        if len(segments) < 2:
            return {"count": 0, "avg_ms": 0, "max_ms": 0}
        
        pauses = []
        pause_threshold_ms = 500  # Pauses longer than 500ms
        
        for i in range(1, len(segments)):
            prev_end = segments[i-1].get("end", 0)
            curr_start = segments[i].get("start", 0)
            gap_ms = (curr_start - prev_end) * 1000
            
            if gap_ms > pause_threshold_ms:
                pauses.append(gap_ms)
        
        if not pauses:
            return {"count": 0, "avg_ms": 0, "max_ms": 0}
        
        return {
            "count": len(pauses),
            "avg_ms": sum(pauses) / len(pauses),
            "max_ms": max(pauses)
        }
    
    def _check_grammar(self, text: str) -> List[Dict]:
        """Check grammar using spaCy (basic) and patterns."""
        errors = []
        
        if not self.nlp:
            return errors
        
        doc = self.nlp(text)
        
        # Basic grammar checks
        for sent in doc.sents:
            sent_text = sent.text.strip()
            
            # Check for subject-verb agreement (simplified)
            # This is a basic check - for production, use language_tool_python
            
            # Check sentence starts with capital
            if sent_text and not sent_text[0].isupper():
                errors.append({
                    "error": "Sentence should start with capital letter",
                    "text": sent_text[:50],
                    "suggestion": sent_text[0].upper() + sent_text[1:],
                    "type": "capitalization"
                })
            
            # Check for double words
            words = sent_text.split()
            for i in range(len(words) - 1):
                if words[i].lower() == words[i+1].lower() and words[i].isalpha():
                    errors.append({
                        "error": f"Repeated word: '{words[i]}'",
                        "text": f"...{words[i]} {words[i+1]}...",
                        "suggestion": words[i],
                        "type": "repetition"
                    })
        
        return errors
    
    def _calculate_grammar_score(self, errors: List[Dict], text: str) -> float:
        """Calculate grammar score (0-5) based on error density."""
        if not text:
            return 0
        
        word_count = len(text.split())
        error_count = len(errors)
        
        # Error rate per 100 words
        error_rate = (error_count / word_count) * 100 if word_count > 0 else 0
        
        # Convert to 0-5 score (fewer errors = higher score)
        if error_rate == 0:
            return 5.0
        elif error_rate < 1:
            return 4.5
        elif error_rate < 2:
            return 4.0
        elif error_rate < 5:
            return 3.0
        elif error_rate < 10:
            return 2.0
        else:
            return 1.0
    
    def _analyze_vocabulary(self, text: str) -> Tuple[str, float]:
        """Analyze vocabulary level and diversity."""
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        if not words:
            return "unknown", 0
        
        unique_words = set(words)
        unique_ratio = len(unique_words) / len(words)
        
        # Estimate vocabulary level using average word length and complexity
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        # Check for advanced vocabulary indicators
        syllable_count = textstat.syllable_count(text)
        avg_syllables = syllable_count / len(words) if words else 0
        
        if avg_syllables > 2.5 and avg_word_length > 7:
            level = "advanced"
        elif avg_syllables > 1.8 and avg_word_length > 5:
            level = "intermediate"
        else:
            level = "basic"
        
        return level, unique_ratio
    
    def _avg_sentence_length(self, text: str) -> float:
        """Calculate average sentence length."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0
        
        total_words = sum(len(s.split()) for s in sentences)
        return total_words / len(sentences)
    
    def _calculate_clarity_score(
        self,
        text: str,
        grammar_errors: List[Dict],
        flesch_score: float
    ) -> float:
        """Calculate overall clarity score (0-5)."""
        # Base score from readability
        if flesch_score >= 80:
            base = 5.0
        elif flesch_score >= 60:
            base = 4.0
        elif flesch_score >= 40:
            base = 3.0
        elif flesch_score >= 20:
            base = 2.0
        else:
            base = 1.0
        
        # Deduct for grammar errors
        error_penalty = min(len(grammar_errors) * 0.1, 1.0)
        
        return max(base - error_penalty, 0)
    
    def _calculate_conciseness_score(self, text: str) -> float:
        """Calculate conciseness score (0-5)."""
        words = text.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0
        
        # Count filler words
        filler_count, _ = self._count_fillers(text)
        filler_ratio = filler_count / word_count
        
        # Count wordy phrases
        wordy_phrases = [
            "in order to", "due to the fact that", "at this point in time",
            "in the event that", "for the purpose of", "in spite of the fact"
        ]
        wordy_count = sum(text.lower().count(phrase) for phrase in wordy_phrases)
        
        # Calculate score
        base = 5.0
        base -= filler_ratio * 10  # Penalize fillers
        base -= wordy_count * 0.5  # Penalize wordy phrases
        
        return max(min(base, 5.0), 0)
    
    def _empty_language_metrics(self) -> LanguageMetrics:
        """Return empty metrics for empty text."""
        return LanguageMetrics(
            grammar_errors=[],
            grammar_score=0,
            vocabulary_level="unknown",
            unique_word_ratio=0,
            avg_sentence_length=0,
            readability_flesch=0,
            readability_flesch_grade=0,
            readability_gunning_fog=0,
            clarity_score=0,
            conciseness_score=0
        )


# Module-level instance
speech_analyzer = SpeechAnalyzer()


def analyze_speech(transcription: Dict[str, Any]) -> SpeechMetrics:
    """Convenience function for speech analysis."""
    return speech_analyzer.analyze_speech(transcription)


def analyze_language(text: str) -> LanguageMetrics:
    """Convenience function for language analysis."""
    return speech_analyzer.analyze_language(text)