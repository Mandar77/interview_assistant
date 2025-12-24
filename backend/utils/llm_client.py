"""
LLM Client - Ollama Integration for Local LLM
Provides a unified interface for interacting with local Ollama models
"""

import ollama
from typing import Optional, List, Dict, Any, Generator
import logging
import json

from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with local Ollama LLM."""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        embedding_model: str = None
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.embedding_model = embedding_model or settings.ollama_embedding_model
        
        # Configure ollama client
        self.client = ollama.Client(host=self.base_url)
        
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            json_mode: If True, expect JSON output
            
        Returns:
            Generated text response
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            options = {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
            
            if json_mode:
                options["format"] = "json"
            
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=options
            )
            
            return response["message"]["content"]
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Stream a completion from the LLM.
        
        Yields:
            Text chunks as they're generated
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = self.client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={"temperature": temperature}
            )
            
            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
                    
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            raise
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from the LLM.
        
        Returns:
            Parsed JSON dictionary
        """
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            json_mode=True
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.debug(f"Raw response: {response}")
            # Try to extract JSON from response
            return self._extract_json(response)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Attempt to extract JSON from text that may have extra content."""
        import re
        
        # Try to find JSON in the text
        patterns = [
            r'\{[\s\S]*\}',  # Match {...}
            r'\[[\s\S]*\]',  # Match [...]
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        
        raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")
    
    def get_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding floats
        """
        try:
            response = self.client.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            return response["embedding"]
            
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        return [self.get_embeddings(text) for text in texts]
    
    def check_health(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            models = self.client.list()
            model_names = [m["name"] for m in models.get("models", [])]
            
            if self.model not in model_names and f"{self.model}:latest" not in model_names:
                logger.warning(f"Model {self.model} not found. Available: {model_names}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False


# Global client instance
llm_client = OllamaClient()


def get_llm_client() -> OllamaClient:
    """Get the global LLM client instance."""
    return llm_client