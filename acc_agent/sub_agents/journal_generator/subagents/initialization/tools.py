"""
Tools for the Journal Initialization subagent
"""

import os
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime
from google.adk.tools import FunctionTool
import glob

def initialize_journal_session(tool_context) -> Dict[str, Any]:
    """
    Initialize journal generation session by loading categorized transactions.
    This is used by the Journal InitializationAgent.
    """
    try:
        # Look for the most recent categorization file
        pattern = "data/output/categorization_results_session_*.jsonl"
        files = glob.glob(pattern)
        
        if not files:
            return {
                "status": "error",
                "error": "No categorization files found. Please run categorization first."
            }
        
        # Get the most recent file
        categorization_file = max(files, key=os.path.getctime)
        filename = os.path.basename(categorization_file)
        categorization_session_id = filename.replace("categorization_results_", "").replace(".jsonl", "")
        
        # Read categorized transactions from JSONL file
        categorized_transactions = []
        metadata = None
        
        with open(categorization_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('# '):
                    # Parse metadata
                    try:
                        metadata = json.loads(line[2:])
                    except:
                        pass
                else:
                    # Parse transaction
                    try:
                        categorized_transactions.append(json.loads(line))
                    except:
                        pass
        
        if not categorized_transactions:
            return {
                "status": "error",
                "error": "No categorized transactions found in file"
            }
        
        # Create journal session ID
        journal_session_id = f"journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Create output directory
        output_dir = "data/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Store in session state
        tool_context.state["journal.session_id"] = journal_session_id
        tool_context.state["journal.categorized_transactions"] = categorized_transactions
        tool_context.state["journal.categorization_session_id"] = categorization_session_id
        tool_context.state["journal.total_transactions"] = len(categorized_transactions)
        tool_context.state["journal.status"] = "initialized"
        tool_context.state["journal.created_at"] = datetime.now().isoformat()
        tool_context.state["journal.categorization_file"] = categorization_file
        tool_context.state["journal.metadata"] = metadata
        
        return {
            "status": "success",
            "journal_session_id": journal_session_id,
            "categorization_session_id": categorization_session_id,
            "total_transactions": len(categorized_transactions),
            "categorization_file": categorization_file,
            "message": f"Journal session initialized with {len(categorized_transactions)} categorized transactions"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Create the tool
initialize_journal_session_tool = FunctionTool(initialize_journal_session) 