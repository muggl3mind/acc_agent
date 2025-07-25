"""
Tools for the Journal Output subagent
"""

import os
import csv
import json
from typing import Dict, List, Any
from datetime import datetime
from google.adk.tools import FunctionTool

def format_and_save_journal_entries(tool_context) -> Dict[str, Any]:
    """
    Format journal entries and save them to CSV file.
    This is used by the Journal OutputAgent.
    """
    try:
        # Get journal entries from session state
        journal_entries = tool_context.state.get("journal.entries", [])
        session_id = tool_context.state.get("journal.session_id", "")
        
        if not journal_entries:
            return {
                "status": "error",
                "error": "No journal entries found in session state"
            }
        
        # Create output file paths
        csv_output_file = f"data/output/journal_entries_{session_id}.csv"
        json_output_file = f"data/output/journal_entries_{session_id}.json"
        
        # Ensure output directory exists
        os.makedirs("data/output", exist_ok=True)
        
        # Prepare CSV data
        csv_headers = [
            "Entry ID", "Transaction ID", "Date", "Account Code", "Account Name", 
            "Description", "Debit", "Credit", "Entry Type"
        ]
        
        # Write CSV file
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_headers)
            
            for entry in journal_entries:
                writer.writerow([
                    entry.get('entry_id', ''),
                    entry.get('transaction_id', ''),
                    entry.get('date', ''),
                    entry.get('account_code', ''),
                    entry.get('account_name', ''),
                    entry.get('description', ''),
                    entry.get('debit', 0.0),
                    entry.get('credit', 0.0),
                    entry.get('entry_type', '')
                ])
        
        # Prepare summary data
        total_debits = sum(entry.get('debit', 0) for entry in journal_entries)
        total_credits = sum(entry.get('credit', 0) for entry in journal_entries)
        unique_transactions = len(set(entry.get('transaction_id', '') for entry in journal_entries))
        
        # Create detailed JSON output with metadata
        json_output = {
            "metadata": {
                "journal_session_id": session_id,
                "categorization_session_id": tool_context.state.get("journal.categorization_session_id", ""),
                "created_at": datetime.now().isoformat(),
                "total_entries": len(journal_entries),
                "total_transactions": unique_transactions,
                "total_debits": total_debits,
                "total_credits": total_credits,
                "entries_balance": abs(total_debits - total_credits) < 0.01,
                "source_file": tool_context.state.get("journal.categorization_file", "")
            },
            "summary": {
                "balance_check": {
                    "total_debits": total_debits,
                    "total_credits": total_credits,
                    "difference": total_debits - total_credits,
                    "is_balanced": abs(total_debits - total_credits) < 0.01
                },
                "account_summary": {}
            },
            "journal_entries": journal_entries
        }
        
        # Generate account summary
        account_summary = {}
        for entry in journal_entries:
            account_code = entry.get('account_code', '')
            account_name = entry.get('account_name', '')
            key = f"{account_code} - {account_name}"
            
            if key not in account_summary:
                account_summary[key] = {"total_debits": 0, "total_credits": 0, "net_amount": 0, "entry_count": 0}
            
            account_summary[key]["total_debits"] += entry.get('debit', 0)
            account_summary[key]["total_credits"] += entry.get('credit', 0)
            account_summary[key]["net_amount"] = account_summary[key]["total_debits"] - account_summary[key]["total_credits"]
            account_summary[key]["entry_count"] += 1
        
        json_output["summary"]["account_summary"] = account_summary
        
        # Write JSON file
        with open(json_output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_output, jsonfile, indent=2, default=str)
        
        # Update session state
        tool_context.state["journal.csv_output_file"] = csv_output_file
        tool_context.state["journal.json_output_file"] = json_output_file
        tool_context.state["journal.status"] = "completed"
        tool_context.state["journal.completed_at"] = datetime.now().isoformat()
        
        return {
            "status": "success",
            "csv_output_file": csv_output_file,
            "json_output_file": json_output_file,
            "total_entries": len(journal_entries),
            "total_transactions": unique_transactions,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "entries_balance": abs(total_debits - total_credits) < 0.01,
            "balance_difference": total_debits - total_credits,
            "message": f"Journal entries saved! {len(journal_entries)} entries from {unique_transactions} transactions. Balance: ${total_debits:,.2f}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Create the tool
format_and_save_journal_entries_tool = FunctionTool(format_and_save_journal_entries) 