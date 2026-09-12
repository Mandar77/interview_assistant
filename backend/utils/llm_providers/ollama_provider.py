"""
Ollama provider — local, self-hosted inference.
Location: backend/utils/llm_providers/ollama_provider.py

Powers the "owned" deployment tier. Carries the schema-constrained output and
context-window handling that took question generation from a 100% OA failure
rate down to zero.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Generator, List, Optional

import ollama

from config.settings import settings
from utils.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Local Ollama inference — the self-hosted "owned" tier."""

    name = "ollama"
    
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
        json_mode: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        num_ctx: Optional[int] = None,
    ) -> str:
        """
        Generate a completion from the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            json_mode: If True, constrain output to valid JSON
            json_schema: If given, constrain output to this exact JSON schema.
                Much stronger than json_mode - the model cannot omit a required
                field or emit a raw newline inside a string. Takes precedence
                over json_mode.
            num_ctx: Context window override; defaults to settings.ollama_num_ctx

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
                "num_ctx": num_ctx or settings.ollama_num_ctx,
            }

            # `format` is a top-level argument on Ollama's chat API, NOT an
            # entry in `options` - putting it there is silently ignored, which
            # left every json_mode caller parsing free-form markdown.
            kwargs: Dict[str, Any] = {}
            if json_schema is not None:
                kwargs["format"] = json_schema
            elif json_mode:
                kwargs["format"] = "json"

            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
                **kwargs
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
    
    def check_health(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            models = self.client.list()
            model_list = models.get("models", [])
            
            # Handle different response formats
            model_names = []
            for m in model_list:
                if isinstance(m, dict):
                    model_names.append(m.get("name", ""))
                    model_names.append(m.get("model", ""))
                elif hasattr(m, "name"):
                    model_names.append(m.name)
                elif hasattr(m, "model"):
                    model_names.append(m.model)
            
            # Clean up names and check
            model_names = [n for n in model_names if n]
            logger.info(f"Available Ollama models: {model_names}")
            
            # Check if our model exists (with or without :latest tag)
            model_base = self.model.split(":")[0]
            found = any(
                model_base in name or self.model in name 
                for name in model_names
            )
            
            if not found:
                logger.warning(f"Model {self.model} not found. Available: {model_names}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            logger.debug(f"Exception details: {type(e).__name__}: {e}")
            return False
