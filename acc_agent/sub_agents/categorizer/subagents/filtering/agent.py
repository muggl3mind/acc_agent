"""
Filtering subagent for analyzing categorization results
"""

import os
from google.adk.agents import LlmAgent
from dotenv import load_dotenv
from .prompt import FILTERING_PROMPT
from .tools import read_and_filter_results_tool

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# Filtering Agent
filtering_agent = LlmAgent(
    model=MODEL,
    name="FilteringAgent",
    description="Analyzes categorization results and provides confidence-based filtering and recommendations",
    tools=[read_and_filter_results_tool],
    instruction=FILTERING_PROMPT,
    output_key="filtering_result"
) 