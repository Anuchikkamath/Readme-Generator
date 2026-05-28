"""
Diagram Generator Module
Generates Mermaid diagram source from README content using OpenAI.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class DiagramGenerator:
    """Generate Mermaid chart definitions from README markdown text."""

    ALLOWED_KINDS = {
        "flowchart",
        "sequence",
        "class",
        "er",
        "journey",
        "state",
        "mindmap",
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY in .env file or pass api_key parameter."
            )

    def _call_llm(self, messages: list, temperature: float = 0.2, max_tokens: int = 1800) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=120,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    @staticmethod
    def _basic_mermaid_guardrails(diagram_code: str) -> str:
        blocked_tokens = ["<script", "javascript:", "onerror=", "onclick="]
        lower = diagram_code.lower()
        for token in blocked_tokens:
            if token in lower:
                raise ValueError("Unsafe Mermaid content detected")
        return diagram_code

    def generate(self, readme_content: str, diagram_kind: str = "flowchart") -> str:
        if not readme_content or not readme_content.strip():
            raise ValueError("README content is empty")

        kind = (diagram_kind or "flowchart").strip().lower()
        if kind not in self.ALLOWED_KINDS:
            raise ValueError(f"Unsupported diagram kind '{diagram_kind}'")

        system_prompt = (
            "You are a software architect who writes valid Mermaid diagrams. "
            "Return only Mermaid source code with no markdown fence and no explanation."
        )

        user_prompt = f"""Create ONE Mermaid {kind} diagram that best summarizes this README.

Rules:
- Output ONLY Mermaid code.
- Must be syntactically valid Mermaid.
- Keep labels concise.
- Avoid HTML in labels.
- Do not include code fences.
- Prefer a single coherent diagram over many disconnected nodes.

README:
{readme_content}
"""

        response_text = self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        cleaned = self._strip_code_fences(response_text)
        cleaned = self._basic_mermaid_guardrails(cleaned)

        if len(cleaned) > 10000:
            raise ValueError("Generated diagram is too large")

        return cleaned
