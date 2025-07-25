"""
Main categorizer agent that coordinates transaction categorization workflow
"""

import os
from google.adk.agents import SequentialAgent, LlmAgent
from dotenv import load_dotenv

# Import subagents from their individual modules
from .subagents.initialization.agent import initialization_agent
from .subagents.parallel_processing.agent import parallel_processing_agent  
from .subagents.filtering.agent import filtering_agent

# Import prompts and tools to create separate instances for the main workflow
from .subagents.initialization.prompt import INITIALIZATION_PROMPT
from .subagents.initialization.tools import initialize_session_and_output_file_tool
from .subagents.filtering.prompt import FILTERING_PROMPT
from .subagents.filtering.tools import read_and_filter_results_tool

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# MAIN CATEGORIZER WORKFLOW - Using fast parallel processing
categorizer_agent = SequentialAgent(
    name="TransactionCategorizationWorkflow", 
    description="Fast parallel transaction categorization workflow using CSV files and chart of accounts with JSONL output",
    sub_agents=[
        initialization_agent,
        parallel_processing_agent,
        filtering_agent
    ]
)

# Export the main workflow (backward compatibility)
parallel_categorizer_agent = categorizer_agent

if __name__ == "__main__":
    from google.adk.runners import run
    run(categorizer_agent) 