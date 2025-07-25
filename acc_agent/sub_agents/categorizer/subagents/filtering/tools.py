"""
Tools for the Filtering subagent
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from google.adk.tools import FunctionTool

def read_and_filter_results(tool_context) -> Dict[str, Any]:
    """
    Read and analyze categorization results from the output file.
    Provides filtering and confidence analysis.
    This is used by FilteringAgent for final result analysis.
    """
    try:
        output_file = tool_context.state.get("categorization.output_file")
        if not output_file:
            return {
                "status": "error",
                "error": "No output file found in session state"
            }
        
        # Read JSONL file
        transactions = []
        metadata = None
        
        with open(output_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Handle metadata comment line
                if line.startswith('# '):
                    try:
                        metadata_json = line[2:]  # Remove '# ' prefix
                        metadata = json.loads(metadata_json)
                    except json.JSONDecodeError:
                        # Skip malformed metadata
                        continue
                    continue
                
                try:
                    transaction = json.loads(line)
                    transactions.append(transaction)
                except json.JSONDecodeError as e:
                    return {
                        "status": "error",
                        "error": f"Invalid JSON on line {line_num}: {str(e)}"
                    }
        
        if not transactions:
            return {
                "status": "error", 
                "error": "No transactions found in output file"
            }
        
        # Analyze confidence levels
        high_confidence = []    # >= 0.9
        medium_confidence = []  # 0.7 - 0.89
        low_confidence = []     # < 0.7
        error_transactions = [] # confidence = 0 or account_code = 'ERROR'
        
        for trans in transactions:
            confidence = float(trans.get('confidence', 0.0))
            account_code = trans.get('account_code', '')
            
            if account_code == 'ERROR' or confidence == 0.0:
                error_transactions.append(trans)
            elif confidence >= 0.9:
                high_confidence.append(trans)
            elif confidence >= 0.7:
                medium_confidence.append(trans)
            else:
                low_confidence.append(trans)
        
        # Calculate statistics
        total_transactions = len(transactions)
        high_confidence_pct = (len(high_confidence) / total_transactions) * 100
        medium_confidence_pct = (len(medium_confidence) / total_transactions) * 100
        low_confidence_pct = (len(low_confidence) / total_transactions) * 100
        error_pct = (len(error_transactions) / total_transactions) * 100
        
        # Account usage analysis
        account_usage = {}
        for trans in transactions:
            account_code = trans.get('account_code', 'UNKNOWN')
            account_name = trans.get('account_name', 'UNKNOWN')
            key = f"{account_code}: {account_name}"
            account_usage[key] = account_usage.get(key, 0) + 1
        
        # Sort by usage frequency
        sorted_accounts = sorted(account_usage.items(), key=lambda x: x[1], reverse=True)
        
        # Transactions needing review (low confidence + errors)
        needs_review = low_confidence + error_transactions
        
        # Build detailed review list
        review_details = []
        for trans in needs_review:
            review_details.append({
                "transaction_id": trans.get('transaction_id', ''),
                "date": trans.get('date', ''),
                "amount": trans.get('amount', 0),
                "description": trans.get('description', '')[:100] + "..." if len(trans.get('description', '')) > 100 else trans.get('description', ''),
                "account_code": trans.get('account_code', ''),
                "account_name": trans.get('account_name', ''),
                "confidence": trans.get('confidence', 0.0),
                "reasoning": trans.get('reasoning', '')
            })
        
        return {
            "status": "success",
            "output_file": output_file,
            "metadata": metadata,
            "summary": {
                "total_transactions": total_transactions,
                "high_confidence_count": len(high_confidence),
                "medium_confidence_count": len(medium_confidence), 
                "low_confidence_count": len(low_confidence),
                "error_count": len(error_transactions),
                "needs_review_count": len(needs_review)
            },
            "confidence_percentages": {
                "high_confidence_pct": round(high_confidence_pct, 1),
                "medium_confidence_pct": round(medium_confidence_pct, 1),
                "low_confidence_pct": round(low_confidence_pct, 1),
                "error_pct": round(error_pct, 1)
            },
            "account_usage": sorted_accounts[:10],  # Top 10 most used accounts
            "transactions_for_review": review_details,
            "high_confidence_transactions": [
                {
                    "transaction_id": t.get('transaction_id', ''),
                    "account_code": t.get('account_code', ''),
                    "account_name": t.get('account_name', ''),
                    "confidence": t.get('confidence', 0.0)
                } for t in high_confidence[:5]  # Show first 5 high confidence
            ]
        }
        
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"Output file not found: {output_file}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Create FunctionTool instances
read_and_filter_results_tool = FunctionTool(read_and_filter_results) 