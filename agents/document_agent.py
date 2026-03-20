"""
Document Agent — analyzes uploaded XLS/PPT/PDF documents for M&A insights.
"""
import json
from typing import Dict, Any

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from utils.state import State
from utils.document_parser import document_parser


class DocumentAgent(BaseAgent):
    """Extracts key M&A metrics and insights from uploaded documents."""

    def __init__(self):
        super().__init__("document")

    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        file_path = state.get("context", {}).get("file_path", "")
        if not file_path:
            return {"error": "No file path provided"}

        # Parse the document
        parsed = document_parser.parse(file_path)
        if "error" in parsed:
            return parsed

        # Extract all text for LLM
        full_text = document_parser.extract_all_text(parsed)

        # Analyze with LLM
        prompt = f"""Analyze this M&A-related document and extract key information.

Document: {parsed.get('filename', 'unknown')} ({parsed.get('type', 'unknown')})
Summary: {parsed.get('summary', '')}

Content (first 4000 chars):
{full_text[:4000]}

Extract and return as JSON:
{{
    "company_name": "<identified company name>",
    "industry": "<identified industry/sector>",
    "key_metrics": {{
        "revenue": "<if found>",
        "ebitda": "<if found>",
        "growth_rate": "<if found>",
        "employees": "<if found>",
        "geography": "<if found>"
    }},
    "document_type": "<CIM | Financial Model | Pitch Deck | Due Diligence | Other>",
    "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
    "strengths": ["<strength 1>", "<strength 2>"],
    "concerns": ["<concern 1>", "<concern 2>"],
    "summary": "<2-3 sentence executive summary>"
}}

Return ONLY valid JSON."""

        messages = self._create_messages(prompt)
        response = await self._call_llm(messages)

        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()
            analysis = json.loads(text)
        except json.JSONDecodeError:
            analysis = {
                "summary": response[:500],
                "key_findings": ["Document parsed but structured extraction failed"],
                "document_type": "Other",
            }

        analysis["parsed_metadata"] = {
            "type": parsed.get("type"),
            "filename": parsed.get("filename"),
            "summary": parsed.get("summary"),
        }
        return analysis
