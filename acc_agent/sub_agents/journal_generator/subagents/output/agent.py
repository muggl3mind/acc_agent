"""
Journal Output subagent for journal generation
"""

import os
from google.adk.agents import LlmAgent
from dotenv import load_dotenv
from .prompt import JOURNAL_OUTPUT_PROMPT
from .tools import format_and_save_journal_entries_tool

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# Journal Output Agent
journal_output_agent = LlmAgent(
    model=MODEL,
    name="JournalOutputAgent",
    description="Formats and saves journal entries to CSV and JSON files with proper accounting structure",
    tools=[format_and_save_journal_entries_tool],
    instruction=JOURNAL_OUTPUT_PROMPT,
    output_key="journal_output_result"
) 