"""
ollama_client.py — Ollama integration for Glass Box

Handles: model discovery, paraphrase, generate, inline ghost completion.
Recommended model: qwen2.5:0.5b (~400MB) — runs on student hardware.
Fallback: rule-based completions when Ollama is unavailable.

All calls are async to avoid blocking the NiceGUI event loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

#  Constants ─
OLLAMA_BASE      = "http://localhost:11434"
DEFAULT_MODEL    = "qwen2.5:0.5b"
FALLBACK_MODEL   = "tinyllama"          # second choice
TIMEOUT_DISCOVER = 2.0                  # fast check — don't hang UI
TIMEOUT_GENERATE = 30.0
MAX_GHOST_TOKENS = 20                   # keep ghost completions short


#  Status dataclass
@dataclass
class OllamaStatus:
    available: bool = False
    models: list[str] = field(default_factory=list)
    active_model: str = ""
    error: str = ""


#  Client
class OllamaClient:
    """
    Async Ollama client. Instantiate once, share across the Editor.

    Usage:
        client = OllamaClient()
        status = await client.discover()
        if status.available:
            result = await client.paraphrase("Some text")
    """

    def __init__(self, base_url: str = OLLAMA_BASE):
        self.base_url    = base_url
        self.status      = OllamaStatus()
        self._http       = httpx.AsyncClient(timeout=TIMEOUT_GENERATE)

    #  Discovery ─

    async def discover(self) -> OllamaStatus:
        """Ping Ollama and enumerate available models. Updates self.status."""
        try:
            resp = await asyncio.wait_for(
                self._http.get(f"{self.base_url}/api/tags"),
                timeout=TIMEOUT_DISCOVER,
            )
            resp.raise_for_status()
            data   = resp.json()
            models = [m["name"] for m in data.get("models", [])]

            # Pick best available model
            active = self._pick_model(models)

            self.status = OllamaStatus(
                available=True,
                models=models,
                active_model=active,
            )
        except (httpx.ConnectError, httpx.TimeoutException, asyncio.TimeoutError):
            self.status = OllamaStatus(
                available=False,
                error="Ollama not running. Install from ollama.com and run: ollama pull qwen2.5:0.5b",
            )
        except Exception as exc:
            self.status = OllamaStatus(available=False, error=str(exc))

        return self.status

    def set_model(self, model: str) -> None:
        self.status.active_model = model

    #  Core generation ─

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Non-streaming generation. Returns full response string."""
        if not self.status.available:
            raise RuntimeError("Ollama unavailable")

        payload = {
            "model":  self.status.active_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["system"] = system

        resp = await self._http.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=TIMEOUT_GENERATE,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    async def generate_stream(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 512,
    ) -> AsyncGenerator[str, None]:
        """Streaming generation — yields tokens as they arrive."""
        if not self.status.available:
            raise RuntimeError("Ollama unavailable")

        payload = {
            "model":  self.status.active_model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": max_tokens, "temperature": 0.7},
        }
        if system:
            payload["system"] = system

        async with self._http.stream(
            "POST", f"{self.base_url}/api/generate",
            json=payload, timeout=TIMEOUT_GENERATE
        ) as resp:
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

    #  Task-specific methods ─

    async def paraphrase(self, text: str) -> str:
        """Rewrite text to improve clarity, preserving meaning."""
        system = (
            "You are an academic writing assistant. "
            "Rewrite the given text to improve clarity and flow. "
            "Preserve all factual content. "
            "Return ONLY the rewritten text, no commentary, no preamble."
        )
        prompt = f"Rewrite this text:\n\n{text}"
        return await self.generate(prompt, system=system, max_tokens=len(text.split()) * 3)

    async def draft_continuation(self, context: str) -> str:
        """Generate a paragraph continuing the given writing context."""
        system = (
            "You are an academic writing assistant. "
            "Continue the text naturally. Write one paragraph only. "
            "Match the style and register of the existing text. "
            "Return ONLY the new paragraph, no commentary."
        )
        # Truncate context to last ~500 chars for small models
        tail = context[-500:] if len(context) > 500 else context
        prompt = f"Continue this academic text:\n\n{tail}"
        return await self.generate(prompt, system=system, max_tokens=200, temperature=0.75)

    async def ghost_completion(self, context: str) -> str:
        """
        Predict the next few words for inline ghost/tab completion.
        Returns at most MAX_GHOST_TOKENS tokens. Short and fast.
        """
        system = (
            "Complete the text with 3-8 natural words only. "
            "Return ONLY the completion words, nothing else."
        )
        tail = context[-200:] if len(context) > 200 else context
        prompt = f"Complete: {tail}"
        result = await self.generate(
            prompt, system=system,
            max_tokens=MAX_GHOST_TOKENS, temperature=0.4
        )
        # Strip to first sentence fragment
        result = result.split(".")[0].split("\n")[0].strip()
        # Guard: don't return more than ~60 chars
        if len(result) > 60:
            result = result[:60].rsplit(" ", 1)[0]
        return result

    async def quote_and_cite(self, selected_text: str, context: str) -> dict:
        """
        Given a selected passage, suggest how to quote it properly
        and flag if it looks like it should be cited.
        Returns: { "quoted": str, "needs_citation": bool, "suggestion": str }
        """
        system = (
            "You are an academic integrity assistant. "
            "Analyse the selected text. "
            "Return a JSON object with these fields: "
            '"quoted" (the text wrapped in proper quotation marks), '
            '"needs_citation" (true if this looks like external content), '
            '"suggestion" (one sentence advice on attribution). '
            "Return ONLY valid JSON."
        )
        prompt = f'Selected text:\n"{selected_text}"\n\nContext:\n{context[-300:]}'
        raw = await self.generate(prompt, system=system, max_tokens=200, temperature=0.2)
        # Strip markdown fences if present
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "quoted": f'"{selected_text}"',
                "needs_citation": True,
                "suggestion": "Consider adding a citation for this passage.",
            }

    #  Fallback rule-based completions (no Ollama) ─

    @staticmethod
    def fallback_completion(context: str) -> str:
        """Simple rule-based ghost completion when Ollama is not available."""
        _CONTINUATIONS = [
            "furthermore, ",
            "in addition, ",
            "however, ",
            "this suggests that ",
            "as a result, ",
            "consequently, ",
        ]
        tail = context.lower().strip()
        if tail.endswith(","):
            return " which"
        if tail.endswith("the"):
            return " following"
        # Rotate based on word count
        words = len(context.split())
        return _CONTINUATIONS[words % len(_CONTINUATIONS)]

    #  Model utilities ─

    @staticmethod
    def _pick_model(models: list[str]) -> str:
        """Pick the best available model from a preference list."""
        preference = [
            "qwen2.5:0.5b",
            "qwen2.5:1.5b",
            "tinyllama",
            "tinyllama:1.1b",
            "phi3:mini",
            "mistral:7b-instruct-q4_0",
            "llama3.2:1b",
        ]
        for preferred in preference:
            for m in models:
                if m.startswith(preferred.split(":")[0]):
                    return m
        return models[0] if models else DEFAULT_MODEL

    async def close(self):
        await self._http.aclose()
