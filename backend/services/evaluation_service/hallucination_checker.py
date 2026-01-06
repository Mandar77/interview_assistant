"""
Hallucination Checker - Verify factual claims in interview responses
Location: backend/services/evaluation_service/hallucination_checker.py
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class ClaimVerification:
    """Result of verifying a single claim."""
    claim: str
    verification_status: str  # verified, unverified, false, uncertain
    confidence: float
    explanation: str
    source: Optional[str] = None


@dataclass
class HallucinationCheckResult:
    """Complete hallucination check result."""
    total_claims: int
    verified_claims: int
    unverified_claims: int
    false_claims: int
    uncertain_claims: int
    hallucination_score: float  # 0-1, lower is better (fewer hallucinations)
    flagged_claims: List[ClaimVerification]
    overall_assessment: str


class HallucinationChecker:
    """
    Check interview responses for potential hallucinations and false claims.
    Uses LLM to extract and verify factual claims.
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    def check(
        self,
        response_text: str,
        question_context: Optional[str] = None,
        domain: str = "software_engineering"
    ) -> HallucinationCheckResult:
        """
        Check response for hallucinations and factual inconsistencies.
        
        Args:
            response_text: The candidate's response
            question_context: The original question for context
            domain: Domain for fact-checking (software_engineering, etc.)
            
        Returns:
            HallucinationCheckResult with verification details
        """
        logger.info("Checking response for hallucinations...")
        
        # Step 1: Extract factual claims from response
        claims = self._extract_claims(response_text, question_context)
        
        if not claims:
            return HallucinationCheckResult(
                total_claims=0,
                verified_claims=0,
                unverified_claims=0,
                false_claims=0,
                uncertain_claims=0,
                hallucination_score=0.0,
                flagged_claims=[],
                overall_assessment="No specific factual claims detected"
            )
        
        # Step 2: Verify each claim
        verifications = []
        for claim in claims:
            verification = self._verify_claim(claim, domain)
            verifications.append(verification)
        
        # Step 3: Aggregate results
        verified = sum(1 for v in verifications if v.verification_status == "verified")
        unverified = sum(1 for v in verifications if v.verification_status == "unverified")
        false_count = sum(1 for v in verifications if v.verification_status == "false")
        uncertain = sum(1 for v in verifications if v.verification_status == "uncertain")
        
        # Calculate hallucination score (0 = no hallucinations, 1 = all hallucinations)
        total = len(verifications)
        if total > 0:
            hallucination_score = (false_count + (uncertain * 0.5) + (unverified * 0.25)) / total
        else:
            hallucination_score = 0.0
        
        # Flag problematic claims
        flagged = [v for v in verifications if v.verification_status in ["false", "uncertain"]]
        
        # Overall assessment
        if hallucination_score < 0.1:
            assessment = "Response appears factually accurate"
        elif hallucination_score < 0.3:
            assessment = "Minor factual concerns detected"
        elif hallucination_score < 0.5:
            assessment = "Several claims need verification"
        else:
            assessment = "Significant factual issues detected"
        
        return HallucinationCheckResult(
            total_claims=total,
            verified_claims=verified,
            unverified_claims=unverified,
            false_claims=false_count,
            uncertain_claims=uncertain,
            hallucination_score=round(hallucination_score, 2),
            flagged_claims=flagged,
            overall_assessment=assessment
        )
    
    def _extract_claims(
        self,
        text: str,
        context: Optional[str] = None
    ) -> List[str]:
        """Extract verifiable factual claims from text."""
        
        system_prompt = """You are an expert at identifying factual claims in text.
Extract specific, verifiable factual claims - NOT opinions or subjective statements.
Focus on technical facts, statistics, comparisons, and definitive statements.
Return ONLY a JSON array of claim strings."""

        context_part = f"\nContext (question asked): {context}" if context else ""
        
        prompt = f"""Extract all verifiable factual claims from this interview response:
{context_part}

RESPONSE:
{text}

Return JSON array of claims. Example:
["Python uses garbage collection for memory management", "REST APIs are stateless by design"]

Extract claims:"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            # Parse JSON array
            import json
            match = re.search(r'\[[\s\S]*?\]', response)
            if match:
                claims = json.loads(match.group())
                return claims[:10]  # Limit to 10 claims
                
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
        
        return []
    
    def _verify_claim(self, claim: str, domain: str) -> ClaimVerification:
        """Verify a single factual claim using LLM knowledge."""
        
        system_prompt = f"""You are a fact-checker specializing in {domain}.
Verify the factual accuracy of claims based on your knowledge.
Be conservative - only mark as "verified" if you're confident it's true.
Mark as "false" only if you're confident it's incorrect.
Use "uncertain" if the claim is partially true or context-dependent.
Use "unverified" if you cannot determine accuracy."""

        prompt = f"""Verify this claim:
"{claim}"

Respond with JSON:
{{
  "status": "verified|false|uncertain|unverified",
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation"
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            import json
            match = re.search(r'\{[\s\S]*?\}', response)
            if match:
                result = json.loads(match.group())
                return ClaimVerification(
                    claim=claim,
                    verification_status=result.get("status", "uncertain"),
                    confidence=result.get("confidence", 0.5),
                    explanation=result.get("explanation", "Unable to verify")
                )
                
        except Exception as e:
            logger.error(f"Claim verification failed: {e}")
        
        return ClaimVerification(
            claim=claim,
            verification_status="uncertain",
            confidence=0.5,
            explanation="Unable to verify claim"
        )
    
    def check_internal_consistency(self, text: str) -> Dict[str, Any]:
        """Check if the response is internally consistent (no contradictions)."""
        
        system_prompt = """Analyze the text for internal contradictions or inconsistencies.
Look for statements that conflict with each other within the same response."""

        prompt = f"""Check this response for internal contradictions:

{text}

Return JSON:
{{
  "is_consistent": true/false,
  "contradictions": [
    {{"statement1": "...", "statement2": "...", "explanation": "..."}}
  ],
  "consistency_score": 0.0-1.0
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            import json
            match = re.search(r'\{[\s\S]*?\}', response)
            if match:
                return json.loads(match.group())
                
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
        
        return {
            "is_consistent": True,
            "contradictions": [],
            "consistency_score": 0.8
        }


# Module-level instance
hallucination_checker = HallucinationChecker()


def check_hallucinations(response_text: str, **kwargs) -> HallucinationCheckResult:
    """Convenience function for hallucination checking."""
    return hallucination_checker.check(response_text, **kwargs)