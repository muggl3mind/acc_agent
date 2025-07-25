"""
Journal Processing subagent for journal generation
"""

import os
from google.adk.agents import LlmAgent
from dotenv import load_dotenv
from .prompt import JOURNAL_PROCESSING_PROMPT
from .tools import process_journal_entries_tool

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# Journal Processing Agent
journal_processing_agent = LlmAgent(
    model=MODEL,
    name="JournalProcessingAgent",
    description="Processes categorized transactions into balanced double-entry journal entries",
    tools=[process_journal_entries_tool],
    instruction=JOURNAL_PROCESSING_PROMPT,
    output_key="journal_processing_result"
) 