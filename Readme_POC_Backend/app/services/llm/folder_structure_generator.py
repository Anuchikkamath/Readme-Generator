"""
Folder Structure Generator Module
Generates project folder structure and basic requirements.txt from Mermaid architecture input.
"""

import json
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class FolderStructureGenerator:
    """Generate folder structure and requirements.txt from architecture diagrams."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY in .env file or pass api_key parameter."
            )

    def _call_llm(self, messages: list, temperature: float = 0.2, max_tokens: int = 2200) -> str:
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
    def _extract_json(response_text: str) -> dict:
        text = (response_text or "").strip()

        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM did not return valid JSON object")

        payload = text[start : end + 1]
        return json.loads(payload)

    def generate(self, mermaid_code: str, diagram_kind: Optional[str] = None, project_name: Optional[str] = None) -> dict:
        diagram = (mermaid_code or "").strip()
        if not diagram:
            raise ValueError("Mermaid diagram input is empty")

        kind = (diagram_kind or "unknown").strip().lower()
        name = (project_name or "GeneratedProject").strip()

        system_prompt = (
            "You are a senior software architect. "
            "Given an architecture diagram in Mermaid, produce a practical starter project layout. "
            "Return only valid JSON with keys folder_structure and requirements_txt."
        )

        user_prompt = f"""Input project name: {name}
Diagram type: {kind}
Architecture (Mermaid):
{diagram}

Create:
1) folder_structure: text tree output suitable for copy/paste.
2) requirements_txt: basic python requirements with common stable libraries that match this architecture.

Constraints:
- Do not include markdown code fences.
- Keep requirements reasonably minimal.
- Include comments in requirements only when useful.

Return ONLY JSON in this exact shape:
{{
  "folder_structure": "...",
  "requirements_txt": "..."
}}
"""

        raw = self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        parsed = self._extract_json(raw)
        folder_structure = (parsed.get("folder_structure") or "").strip()
        requirements_txt = (parsed.get("requirements_txt") or "").strip()

        if not folder_structure:
            raise ValueError("Model returned empty folder_structure")
        if not requirements_txt:
            raise ValueError("Model returned empty requirements_txt")

        return {
            "folder_structure": folder_structure,
            "requirements_txt": requirements_txt,
        }
