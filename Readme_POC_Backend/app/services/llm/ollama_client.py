"""
LLM Client Module
Uses OpenAI's LLM to extract structured data from unstructured meeting notes.
"""

import json
import os
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


class LLMClient:
    """Client for interacting with OpenAI LLM for structured data extraction."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI LLM client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY from .env file)
            model: Model name to use (default: gpt-4o-mini)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. "
                "Set OPENAI_API_KEY in .env file or pass api_key parameter."
            )
    
    def _call_openai(self, messages: list, temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """
        Make API call to OpenAI.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation
            max_tokens: Maximum tokens in response
            
        Returns:
            str: Response text from OpenAI
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    def extract_structured_data(self, notes_text: str, meeting_date: Optional[str] = None) -> dict:
        """
        Extract structured data from unstructured meeting notes using LLM.
        
        Args:
            notes_text: Raw meeting notes text
            meeting_date: Optional meeting date (YYYY-MM-DD format)
            
        Returns:
            dict: Structured data with keys: meeting_date, requirements, tech_stack, 
                  discussions, blockers, conclusions
        """
        # Build date instruction
        if meeting_date:
            date_instruction = f'- meeting_date: Use exactly "{meeting_date}" (this is the confirmed email date in YYYY-MM-DD format).'
        else:
            date_instruction = '- meeting_date: Extract the date from the notes in YYYY-MM-DD format. If no date is found, use null.'
        
        # Construct prompt
        prompt = f"""Extract structured information from the following meeting notes.

Meeting Notes:
{notes_text}

Extract the following information and return ONLY a valid JSON object (no markdown, no code blocks, just JSON):
{date_instruction}
- requirements: Key requirements or requirements discussed
- tech_stack: Technology stack, tools, or frameworks mentioned
- discussions: Main discussion points
- blockers: Blockers or impediments identified
- conclusions: Conclusions or action items

Return ONLY valid JSON, no other text."""

        messages = [
            {"role": "system", "content": "You are a helpful assistant that extracts structured data from meeting notes. Always return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        # Call OpenAI
        response_text = self._call_openai(messages, temperature=0.3)
        
        # Extract JSON from response (handle markdown code blocks, etc.)
        json_str = self._extract_json_from_response(response_text)
        
        # Parse JSON
        try:
            structured_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse: {response_text[:500]}")
        
        # Validate required fields
        required_fields = ['meeting_date', 'requirements', 'tech_stack', 'discussions', 'blockers', 'conclusions']
        for field in required_fields:
            if field not in structured_data:
                if field == 'meeting_date':
                    structured_data[field] = None  # meeting_date can be None
                else:
                    structured_data[field] = ""  # Default to empty string
        
        # Clean meeting_date - ensure it's not the string "None"
        if structured_data.get('meeting_date') == 'None' or str(structured_data.get('meeting_date', '')).strip() == '':
            structured_data['meeting_date'] = None
        
        return structured_data
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from LLM response, handling various formats.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            str: Extracted JSON string
        """
        # Strategy 1: Look for markdown code blocks
        import re
        
        # Try to find JSON in markdown code blocks
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, response_text, re.DOTALL)
        if match:
            return match.group(1)
        
        # Strategy 2: Find JSON object by balanced braces
        start_idx = response_text.find('{')
        if start_idx != -1:
            brace_count = 0
            for i in range(start_idx, len(response_text)):
                if response_text[i] == '{':
                    brace_count += 1
                elif response_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return response_text[start_idx:i+1]
        
        # Strategy 3: Use regex to find JSON-like structure
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        match = re.search(json_pattern, response_text, re.DOTALL)
        if match:
            return match.group(0)
        
        # Fallback: return original text (might fail parsing)
        return response_text.strip()
