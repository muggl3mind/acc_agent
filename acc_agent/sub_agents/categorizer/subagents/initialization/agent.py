"""
Initialization subagent for transaction categorization
"""

import os
from google.adk.agents import LlmAgent
from dotenv import load_dotenv
from .prompt import INITIALIZATION_PROMPT
from .tools import initialize_session_and_output_file_tool

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# Initialization Agent
initialization_agent = LlmAgent(
    model=MODEL,
    name="InitializationAgent",
    description="Initializes categorization session, loads files, validates data, and creates output file",
    tools=[initialize_session_and_output_file_tool],
    instruction=INITIALIZATION_PROMPT,
    output_key="initialization_result"
) 