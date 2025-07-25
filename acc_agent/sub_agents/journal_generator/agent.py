"""
Journal Entry Generation Agent - SequentialAgent workflow
Generates journal entries from categorized transactions using sub-agents
"""

import os
from google.adk.agents import SequentialAgent
from dotenv import load_dotenv

# Import subagents from their individual modules
from .subagents.initialization.agent import journal_initialization_agent
from .subagents.processing.agent import journal_processing_agent
from .subagents.output.agent import journal_output_agent

# Load environment variables
load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.5-pro")

# MAIN JOURNAL WORKFLOW - Using SequentialAgent pattern
journal_agent = SequentialAgent(
    name="JournalEntryGenerationWorkflow",
    description="Complete journal entry generation workflow that loads categorized transactions, processes them into balanced journal entries, and saves the results",
    sub_agents=[
        journal_initialization_agent,
        journal_processing_agent,
        journal_output_agent
    ]
)

# Export the main workflow
journal_sequential_agent = journal_agent

if __name__ == "__main__":
    from google.adk.runners import run
    run(journal_agent) 