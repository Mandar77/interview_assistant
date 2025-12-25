"""
Skill Parser - Extract skills from job descriptions using spaCy + LLM
Location: backend/services/question_service/skill_parser.py
"""

import spacy
from typing import List, Dict, Optional
import logging
import json
import re

from models.schemas import SkillTag, SkillCategory
from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None


# Predefined skill patterns for rule-based extraction
SKILL_PATTERNS = {
    SkillCategory.PROGRAMMING: [
        r'\b(python|java|javascript|typescript|c\+\+|c#|go|golang|rust|ruby|php|swift|kotlin|scala|r)\b',
        r'\b(react|angular|vue|node\.?js|express|django|flask|fastapi|spring|\.net)\b',
        r'\b(html|css|sass|less|tailwind|bootstrap)\b',
    ],
    SkillCategory.DATA_STRUCTURES: [
        r'\b(array|linked\s*list|stack|queue|tree|graph|hash\s*(table|map)|heap|trie)\b',
        r'\b(data\s*structures?|dsa)\b',
    ],
    SkillCategory.ALGORITHMS: [
        r'\b(algorithm|sorting|searching|dynamic\s*programming|recursion|backtracking)\b',
        r'\b(big\s*o|time\s*complexity|space\s*complexity)\b',
        r'\b(bfs|dfs|dijkstra|binary\s*search)\b',
    ],
    SkillCategory.SYSTEM_DESIGN: [
        r'\b(system\s*design|architecture|scalab(le|ility)|distributed\s*system)\b',
        r'\b(microservices?|monolith|api\s*design|rest(ful)?|graphql|grpc)\b',
        r'\b(load\s*balanc(er|ing)|caching|cdn|message\s*queue)\b',
        r'\b(kafka|rabbitmq|redis|memcached|nginx)\b',
    ],
    SkillCategory.DATABASE: [
        r'\b(sql|mysql|postgresql|postgres|oracle|sql\s*server)\b',
        r'\b(nosql|mongodb|cassandra|dynamodb|firebase)\b',
        r'\b(database|db|rdbms|orm|query\s*optimization)\b',
    ],
    SkillCategory.CLOUD: [
        r'\b(aws|amazon\s*web\s*services|ec2|s3|lambda|rds|ecs|eks)\b',
        r'\b(azure|gcp|google\s*cloud|cloud\s*computing)\b',
        r'\b(docker|kubernetes|k8s|terraform|ansible|ci\s*/?\s*cd)\b',
        r'\b(devops|infrastructure|iaac|cloud\s*native)\b',
    ],
    SkillCategory.SOFT_SKILLS: [
        r'\b(communication|leadership|teamwork|collaboration|problem[\s-]*solving)\b',
        r'\b(agile|scrum|kanban|project\s*management)\b',
        r'\b(mentor(ing)?|cross[\s-]*functional)\b',
    ],
}


class SkillParser:
    """Parse job descriptions to extract structured skill tags."""
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.nlp = nlp
    
    def parse(self, job_description: str, use_llm: bool = True) -> List[SkillTag]:
        """
        Extract skills from a job description.
        
        Args:
            job_description: Full text of job description
            use_llm: Whether to use LLM for enhanced extraction
            
        Returns:
            List of SkillTag objects with categorized skills
        """
        # Step 1: Rule-based extraction using regex patterns
        rule_based_skills = self._extract_with_patterns(job_description)
        logger.info(f"Rule-based extraction found {len(rule_based_skills)} skills")
        
        # Step 2: spaCy NER extraction for additional context
        if self.nlp:
            spacy_skills = self._extract_with_spacy(job_description)
            logger.info(f"spaCy extraction found {len(spacy_skills)} entities")
        else:
            spacy_skills = []
        
        # Step 3: LLM-based extraction for comprehensive coverage
        if use_llm:
            try:
                llm_skills = self._extract_with_llm(job_description)
                logger.info(f"LLM extraction found {len(llm_skills)} skills")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")
                llm_skills = []
        else:
            llm_skills = []
        
        # Step 4: Merge and deduplicate
        all_skills = self._merge_skills(rule_based_skills, spacy_skills, llm_skills)
        
        # Step 5: Calculate importance scores
        scored_skills = self._score_skills(all_skills, job_description)
        
        # Sort by importance
        scored_skills.sort(key=lambda x: x.importance, reverse=True)
        
        return scored_skills
    
    def _extract_with_patterns(self, text: str) -> List[Dict]:
        """Extract skills using predefined regex patterns."""
        text_lower = text.lower()
        skills = []
        
        for category, patterns in SKILL_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    skill_name = match.strip() if isinstance(match, str) else match[0].strip()
                    skills.append({
                        "skill": skill_name.title(),
                        "category": category,
                        "source": "pattern"
                    })
        
        return skills
    
    def _extract_with_spacy(self, text: str) -> List[Dict]:
        """Extract skills using spaCy NER and noun chunks."""
        doc = self.nlp(text)
        skills = []
        
        # Extract relevant noun chunks
        tech_indicators = {"experience", "knowledge", "skills", "proficiency", "expertise", "familiar"}
        
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.lower()
            # Check if this noun chunk is near a tech indicator
            if any(ind in chunk.root.head.text.lower() for ind in tech_indicators):
                skills.append({
                    "skill": chunk.text.strip(),
                    "category": SkillCategory.PROGRAMMING,  # Default, will be recategorized
                    "source": "spacy"
                })
        
        return skills
    
    def _extract_with_llm(self, job_description: str) -> List[Dict]:
        """Use LLM for comprehensive skill extraction."""
        
        system_prompt = """You are a technical recruiter expert at parsing job descriptions.
Extract ALL technical and soft skills mentioned or implied in the job description.
Categorize each skill into one of these categories:
- programming: Languages, frameworks, libraries
- data_structures: DS knowledge
- algorithms: Algorithm knowledge
- system_design: Architecture, scalability, distributed systems
- database: SQL, NoSQL, data modeling
- cloud: Cloud platforms, DevOps, infrastructure
- soft_skills: Communication, leadership, teamwork

Return ONLY valid JSON in this exact format:
{
  "skills": [
    {"skill": "Python", "category": "programming", "keywords": ["python", "py"]},
    {"skill": "System Design", "category": "system_design", "keywords": ["architecture", "scalable"]}
  ]
}"""

        prompt = f"""Extract all skills from this job description:

{job_description}

Return the JSON with extracted skills:"""

        try:
            response = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            skills = []
            for item in response.get("skills", []):
                category_str = item.get("category", "programming").lower()
                try:
                    category = SkillCategory(category_str)
                except ValueError:
                    category = SkillCategory.PROGRAMMING
                
                skills.append({
                    "skill": item.get("skill", ""),
                    "category": category,
                    "keywords": item.get("keywords", []),
                    "source": "llm"
                })
            
            return skills
            
        except Exception as e:
            logger.error(f"LLM skill extraction error: {e}")
            return []
    
    def _merge_skills(self, *skill_lists) -> List[Dict]:
        """Merge and deduplicate skills from multiple sources."""
        seen = set()
        merged = []
        
        for skill_list in skill_lists:
            for skill in skill_list:
                skill_lower = skill["skill"].lower().strip()
                if skill_lower and skill_lower not in seen:
                    seen.add(skill_lower)
                    merged.append(skill)
        
        return merged
    
    def _score_skills(self, skills: List[Dict], job_description: str) -> List[SkillTag]:
        """Calculate importance scores based on frequency and position."""
        text_lower = job_description.lower()
        text_length = len(text_lower)
        
        scored = []
        for skill in skills:
            skill_name = skill["skill"].lower()
            
            # Frequency score
            count = text_lower.count(skill_name)
            freq_score = min(count / 5, 1.0)  # Cap at 5 mentions
            
            # Position score (skills mentioned earlier are often more important)
            first_pos = text_lower.find(skill_name)
            if first_pos >= 0:
                pos_score = 1 - (first_pos / text_length)
            else:
                pos_score = 0.5
            
            # Combined importance
            importance = (freq_score * 0.6) + (pos_score * 0.4)
            importance = round(min(max(importance, 0.1), 1.0), 2)
            
            scored.append(SkillTag(
                skill=skill["skill"],
                category=skill["category"],
                importance=importance,
                keywords=skill.get("keywords", [])
            ))
        
        return scored
    
    def get_skill_summary(self, skills: List[SkillTag]) -> Dict[str, List[str]]:
        """Group skills by category for summary view."""
        summary = {}
        for skill in skills:
            cat_name = skill.category.value
            if cat_name not in summary:
                summary[cat_name] = []
            summary[cat_name].append(skill.skill)
        return summary


# Module-level instance
skill_parser = SkillParser()


def parse_job_description(job_description: str, use_llm: bool = True) -> List[SkillTag]:
    """Convenience function for parsing job descriptions."""
    return skill_parser.parse(job_description, use_llm)