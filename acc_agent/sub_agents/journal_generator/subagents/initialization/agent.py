"""
Journal Initialization subagent for journal generation
"""

import os
from google.adk.agents import LlmAgent
from dotenv import load_dotenv
from .prompt import JOURNAL_INITIALIZATION_PROMPT
from .tools import initialize_journal_session_tool

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# Journal Initialization Agent
journal_initialization_agent = LlmAgent(
    model=MODEL,
    name="JournalInitializationAgent",
    description="Initializes journal generation session by loading categorized transactions and setting up session state",
    tools=[initialize_journal_session_tool],
    instruction=JOURNAL_INITIALIZATION_PROMPT,
    output_key="journal_initialization_result"
) 