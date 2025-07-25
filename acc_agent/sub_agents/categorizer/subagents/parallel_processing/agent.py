"""
Parallel Processing subagent for fast transaction categorization
"""

import os
from google.adk.agents import LlmAgent
from dotenv import load_dotenv
from .prompt import PARALLEL_PROCESSING_PROMPT
from .tools import process_all_chunks_parallel_tool

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# Parallel Processing Agent
parallel_processing_agent = LlmAgent(
    model=MODEL,
    name="ParallelProcessingAgent",
    description="Processes all chunks in parallel for much faster categorization",
    tools=[process_all_chunks_parallel_tool],
    instruction=PARALLEL_PROCESSING_PROMPT,
    output_key="parallel_processing_result"
) 