"""
Tools for the Journal Processing subagent
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from google.adk.tools import FunctionTool
import uuid

def process_journal_entries(tool_context) -> Dict[str, Any]:
    """
    Process categorized transactions into journal entries using double-entry bookkeeping rules.
    This is used by the Journal ProcessingAgent.
    """
    try:
        print(f"🔍 JOURNAL PROCESSING DEBUG: Starting processing")
        
        # Check what session state we received from initialization
        received_session_id = tool_context.state.get("journal.session_id")
        received_transactions = tool_context.state.get("journal.categorized_transactions", [])
        received_status = tool_context.state.get("journal.status")
        
        print(f"🔍 JOURNAL PROCESSING DEBUG: Received session_id: {received_session_id}")
        print(f"🔍 JOURNAL PROCESSING DEBUG: Received transactions count: {len(received_transactions)}")
        print(f"🔍 JOURNAL PROCESSING DEBUG: Received status: {received_status}")
        
        # CHOICE POINT: Use session state vs file-based approach
        if received_transactions and received_session_id:
            print(f"🔍 JOURNAL PROCESSING DEBUG: Using session state data (proper workflow)")
            categorized_transactions = received_transactions
            categorization_file = tool_context.state.get("journal.categorization_file", "from_session_state")
        else:
            print(f"🔍 JOURNAL PROCESSING DEBUG: Session state missing/empty, falling back to file read")
            # FIXED: Read from updated file instead of stale session state
            import glob
            import os
            
            # Look for the most recent categorization file (same logic as initialization agent)
            pattern = "data/output/categorization_results_session_*.jsonl"
            files = glob.glob(pattern)
            
            if not files:
                return {
                    "status": "error",
                    "error": "No categorization files found. Please run categorization first."
                }
            
            # Get the most recent file
            categorization_file = max(files, key=os.path.getctime)
            print(f"🔍 JOURNAL PROCESSING DEBUG: Reading from file: {categorization_file}")
            
            # Read categorized transactions from JSONL file (updated data, not stale session state)
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
        
        print(f"🔍 JOURNAL PROCESSING DEBUG: Processing {len(categorized_transactions)} transactions")
        
        if not categorized_transactions:
            return {
                "status": "error",
                "error": "No categorized transactions found"
            }
        
        journal_entries = []
        entry_id = 1
        
        for trans in categorized_transactions:
            # Extract transaction details
            transaction_id = trans.get('transaction_id', '')
            date = trans.get('date', '')
            description = trans.get('description', '')
            amount = float(trans.get('amount', 0))
            account_code = trans.get('account_code', '')
            account_name = trans.get('account_name', '')
            
            # Skip if missing critical data
            if not account_code or amount == 0:
                continue
            
            # Double-entry bookkeeping rules
            if amount > 0:
                # Money coming in (positive amount)
                # Debit Cash (increase asset), Credit the categorized account
                journal_entries.extend([
                    {
                        "entry_id": entry_id,
                        "transaction_id": transaction_id,
                        "date": date,
                        "account_code": "1000",
                        "account_name": "Cash",
                        "description": description,
                        "debit": amount,
                        "credit": 0.0,
                        "entry_type": "debit"
                    },
                    {
                        "entry_id": entry_id,
                        "transaction_id": transaction_id,
                        "date": date,
                        "account_code": account_code,
                        "account_name": account_name,
                        "description": description,
                        "debit": 0.0,
                        "credit": amount,
                        "entry_type": "credit"
                    }
                ])
            else:
                # Money going out (negative amount)
                # Credit Cash (decrease asset), Debit the categorized account
                abs_amount = abs(amount)
                journal_entries.extend([
                    {
                        "entry_id": entry_id,
                        "transaction_id": transaction_id,
                        "date": date,
                        "account_code": "1000",
                        "account_name": "Cash",
                        "description": description,
                        "debit": 0.0,
                        "credit": abs_amount,
                        "entry_type": "credit"
                    },
                    {
                        "entry_id": entry_id,
                        "transaction_id": transaction_id,
                        "date": date,
                        "account_code": account_code,
                        "account_name": account_name,
                        "description": description,
                        "debit": abs_amount,
                        "credit": 0.0,
                        "entry_type": "debit"
                    }
                ])
            
            entry_id += 1
        
        # Validation: Check that total debits equal total credits
        total_debits = sum(entry['debit'] for entry in journal_entries)
        total_credits = sum(entry['credit'] for entry in journal_entries)
        
        if abs(total_debits - total_credits) > 0.01:  # Allow for small rounding errors
            return {
                "status": "error",
                "error": f"Journal entries don't balance! Total debits: {total_debits}, Total credits: {total_credits}"
            }
        
        print(f"🔍 JOURNAL PROCESSING DEBUG: Generated {len(journal_entries)} journal entries, balanced at ${total_debits:,.2f}")
        
        # CRITICAL: Store in session state for output agent
        print(f"🔍 JOURNAL PROCESSING DEBUG: Storing data in session state for output agent...")
        
        # Preserve session_id from initialization if it exists, otherwise create one
        session_id_to_store = received_session_id or f"journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        print(f"🔍 JOURNAL PROCESSING DEBUG: Using session_id: {session_id_to_store}")
        
        tool_context.state["journal.entries"] = journal_entries
        tool_context.state["journal.session_id"] = session_id_to_store  # CRITICAL: Make sure this is set!
        tool_context.state["journal.total_entries"] = len(journal_entries)
        tool_context.state["journal.total_debits"] = total_debits
        tool_context.state["journal.total_credits"] = total_credits
        tool_context.state["journal.status"] = "processed"
        tool_context.state["journal.processed_at"] = datetime.now().isoformat()
        tool_context.state["journal.source_file"] = categorization_file  # Track which file was used
        
        # Verify session state was stored correctly
        print(f"🔍 JOURNAL PROCESSING DEBUG: Verifying session state storage...")
        stored_session_id = tool_context.state.get("journal.session_id")
        stored_entries_count = len(tool_context.state.get("journal.entries", []))
        print(f"🔍 JOURNAL PROCESSING DEBUG: Verified - journal.session_id: {stored_session_id}")
        print(f"🔍 JOURNAL PROCESSING DEBUG: Verified - entries count: {stored_entries_count}")
        
        return {
            "status": "success",
            "total_entries": len(journal_entries),
            "total_transactions": len(categorized_transactions),
            "total_debits": total_debits,
            "total_credits": total_credits,
            "entries_balance": total_debits == total_credits,
            "source_file": categorization_file,
            "message": f"Generated {len(journal_entries)} journal entries from {len(categorized_transactions)} transactions. Entries balance: ${total_debits:,.2f}"
        }
        
    except Exception as e:
        print(f"🔍 JOURNAL PROCESSING DEBUG: Exception occurred: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# Create the tool
process_journal_entries_tool = FunctionTool(process_journal_entries) 