"""
Tools for the journal generator sub-agent
"""

from typing import Dict, List, Any
from datetime import datetime
from google.adk.tools import FunctionTool

def generate_journal_entries(
    categorized_transactions: List[Dict[str, Any]],
    bank_account_code: str = "1000"
) -> Dict[str, Any]:
    """
    Generate journal entries from categorized bank transactions.
    
    Args:
        categorized_transactions: List of categorized transaction dictionaries
        bank_account_code: Account code for the bank/cash account (default: "1000" for cash)
        
    Returns:
        Dictionary containing journal entries and summary information
        
    Note:
        For bank export transactions, account code "1000" is used as the standard cash account.
        All bank transactions involve this cash account plus one other account.
    """
    # Use default bank account code for cash transactions
    if not bank_account_code:
        bank_account_code = "1000"
        
    journal_entries = []
    entry_number = 1
    
    for transaction in categorized_transactions:
        entry = create_journal_entry(transaction, bank_account_code, entry_number)
        journal_entries.append(entry)
        entry_number += 1
    
    # Validate all entries balance
    validation_results = validate_journal_entries(journal_entries)
    
    return {
        'journal_entries': journal_entries,
        'summary': {
            'total_entries': len(journal_entries),
            'validation': validation_results,
            'date_range': get_date_range(journal_entries),
            'total_debits': sum(e.get('debit_amount', 0) for e in journal_entries),
            'total_credits': sum(e.get('credit_amount', 0) for e in journal_entries)
        }
    }

def format_journal_entries_csv(journal_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format journal entries for CSV export."""
    csv_entries = []
    
    for entry in journal_entries:
        # Debit line
        csv_entries.append({
            'Date': entry['date'],
            'Entry_Number': entry['entry_number'],
            'Account': entry['debit_account'],
            'Description': entry['description'],
            'Reference': entry.get('reference', ''),
            'Debit': entry['debit_amount'],
            'Credit': ''
        })
        
        # Credit line
        csv_entries.append({
            'Date': entry['date'],
            'Entry_Number': entry['entry_number'],
            'Account': entry['credit_account'],
            'Description': entry['description'],
            'Reference': entry.get('reference', ''),
            'Debit': '',
            'Credit': entry['credit_amount']
        })
    
    return csv_entries

# Helper functions
def create_journal_entry(transaction: Dict[str, Any], bank_account_code: str, entry_number: int) -> Dict[str, Any]:
    """Create a journal entry from a categorized transaction."""
    amount = float(str(transaction.get('amount', 0)).replace(',', ''))
    
    # Determine debit/credit based on transaction type
    if amount > 0:
        # Positive amount - money coming in (debit bank, credit revenue/income account)
        debit_account = bank_account_code
        debit_amount = amount
        credit_account = transaction.get('account_code', '4000')
        credit_amount = amount
    else:
        # Negative amount - money going out (debit expense account, credit bank)
        debit_account = transaction.get('account_code', '5000')
        debit_amount = abs(amount)
        credit_account = bank_account_code
        credit_amount = abs(amount)
    
    return {
        'entry_number': entry_number,
        'date': transaction.get('date', ''),
        'description': transaction.get('description', ''),
        'reference': transaction.get('transaction_id', ''),
        'debit_account': debit_account,
        'debit_amount': debit_amount,
        'credit_account': credit_account,
        'credit_amount': credit_amount,
        'category': transaction.get('category', ''),
        'confidence': transaction.get('confidence', 0)
    }

def validate_journal_entries(journal_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate that all journal entries balance."""
    total_debits = sum(e.get('debit_amount', 0) for e in journal_entries)
    total_credits = sum(e.get('credit_amount', 0) for e in journal_entries)
    
    balanced = abs(total_debits - total_credits) < 0.01
    
    return {
        'balanced': balanced,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'difference': abs(total_debits - total_credits),
        'entry_count': len(journal_entries)
    }

def get_date_range(journal_entries: List[Dict[str, Any]]) -> str:
    """Get the date range for journal entries."""
    if not journal_entries:
        return 'N/A'
    
    dates = [entry.get('date', '') for entry in journal_entries if entry.get('date')]
    if not dates:
        return 'N/A'
    
    min_date = min(dates)
    max_date = max(dates)
    
    if min_date == max_date:
        return min_date
    else:
        return f"{min_date} to {max_date}"

def load_categorized_transactions(file_path: str) -> Dict[str, Any]:
    """
    Load categorized transactions from a finalized JSON file.
    
    Args:
        file_path: Path to the finalized categorization JSON file
        
    Returns:
        Dictionary containing the categorized transactions and metadata
    """
    import json
    import os
    
    try:
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "error": f"File not found: {file_path}"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categorized_transactions = data.get('categorized_transactions', [])
        
        return {
            "status": "success",
            "categorized_transactions": categorized_transactions,
            "session_id": data.get('session_id', ''),
            "total_transactions": len(categorized_transactions),
            "summary": data.get('summary', {})
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def get_categorized_transactions_from_session(tool_context) -> Dict[str, Any]:
    """
    Get categorized transactions with robust fallback to avoid OpenTelemetry context issues.
    
    Args:
        tool_context: The tool context containing session state
        
    Returns:
        Dictionary containing the categorized transactions and metadata
    """
    try:
        # FIRST: Try direct file access to avoid OpenTelemetry context issues
        import glob
        import os
        import json
        
        # Look for recent categorization files
        pattern = "data/output/categorization_results_session_*.jsonl"
        files = glob.glob(pattern)
        
        if files:
            # Get the most recent file
            output_file = max(files, key=os.path.getctime)
            filename = os.path.basename(output_file)
            session_id = filename.replace("categorization_results_", "").replace(".jsonl", "")
            
            # Read JSONL format
            categorizations = []
            metadata = None
            
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('# '):
                        try:
                            metadata = json.loads(line[2:])
                        except:
                            pass
                    else:
                        try:
                            categorizations.append(json.loads(line))
                        except:
                            pass
            
            return {
                "status": "success",
                "categorized_transactions": categorizations,
                "total_transactions": len(categorizations),
                "session_id": session_id,
                "metadata": metadata,
                "source": "direct_file_access_primary",
                "note": "Used direct file access to avoid OpenTelemetry context issues"
            }
        
        # FALLBACK: Try session state access if no files found
        try:
            output_file = tool_context.state.get("categorization.output_file")
            session_id = tool_context.state.get("categorization.session_id")
            
            if output_file and os.path.exists(output_file):
                # Read JSONL format
                categorizations = []
                metadata = None
                
                with open(output_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith('# '):
                            try:
                                metadata = json.loads(line[2:])
                            except:
                                pass
                        else:
                            try:
                                categorizations.append(json.loads(line))
                            except:
                                pass
                
                return {
                    "status": "success",
                    "categorized_transactions": categorizations,
                    "total_transactions": len(categorizations),
                    "session_id": session_id,
                    "metadata": metadata,
                    "source": "session_state_fallback"
                }
        except Exception as session_error:
            # Session state access failed, but we already tried direct file access
            pass
        
        # If we reach here, no files were found
        return {
            "status": "error",
            "error": "No categorization files found in both direct file access and session state"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"All access methods failed: {str(e)}"
        }

def get_categorized_transactions_direct(
    categorized_transactions: List[Dict[str, Any]],
    session_id: str = ""
) -> Dict[str, Any]:
    """
    Accept categorized transactions directly as input parameter.
    This eliminates the need for session state access and context issues.
    
    Args:
        categorized_transactions: List of categorized transaction dictionaries
        session_id: Optional session ID for tracking
        
    Returns:
        Dictionary containing the categorized transactions and metadata
    """
    try:
        if not categorized_transactions:
            return {
                "status": "error",
                "error": "No categorized transactions provided"
            }
        
        # Validate transaction format
        for i, trans in enumerate(categorized_transactions):
            required_fields = ['transaction_id', 'account_code', 'account_name', 'amount']
            missing_fields = [field for field in required_fields if field not in trans]
            if missing_fields:
                return {
                    "status": "error",
                    "error": f"Transaction {i} missing required fields: {missing_fields}"
                }
        
        return {
            "status": "success",
            "categorized_transactions": categorized_transactions,
            "total_transactions": len(categorized_transactions),
            "session_id": session_id,
            "source": "direct_input"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def get_categorized_transactions_context_free() -> Dict[str, Any]:
    """
    Get categorized transactions without any context dependency.
    Uses direct file access to find and read the most recent categorization file.
    This completely avoids OpenTelemetry context issues.
    
    Returns:
        Dictionary containing the categorized transactions and metadata
    """
    try:
        import glob
        import os
        import json
        
        # Look for recent categorization files
        pattern = "data/output/categorization_results_session_*.jsonl"
        files = glob.glob(pattern)
        
        if not files:
            return {
                "status": "error",
                "error": "No categorization files found"
            }
        
        # Get the most recent file
        output_file = max(files, key=os.path.getctime)
        filename = os.path.basename(output_file)
        session_id = filename.replace("categorization_results_", "").replace(".jsonl", "")
        
        # Read JSONL format
        categorizations = []
        metadata = None
        
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('# '):
                    try:
                        metadata = json.loads(line[2:])
                    except:
                        pass
                else:
                    try:
                        categorizations.append(json.loads(line))
                    except:
                        pass
        
        return {
            "status": "success",
            "categorized_transactions": categorizations,
            "total_transactions": len(categorizations),
            "session_id": session_id,
            "metadata": metadata,
            "source": "context_free_direct_access",
            "file_path": output_file
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Create FunctionTool instances
generate_journal_entries_tool = FunctionTool(generate_journal_entries)
format_journal_entries_csv_tool = FunctionTool(format_journal_entries_csv)
load_categorized_transactions_tool = FunctionTool(load_categorized_transactions)
get_categorized_transactions_from_session_tool = FunctionTool(get_categorized_transactions_from_session)
get_categorized_transactions_direct_tool = FunctionTool(get_categorized_transactions_direct)
get_categorized_transactions_context_free_tool = FunctionTool(get_categorized_transactions_context_free) 