"""
Tools for the Initialization subagent
"""

import os
import json
import csv
import uuid
from typing import Dict, List, Any
from datetime import datetime
from google.adk.tools import FunctionTool

# Configuration
CHUNK_SIZE = 26

def read_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read a CSV file and return its contents as a list of dictionaries.
    Combines Description and Memo fields into a single Description field.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            transactions = []
            
            for row in reader:
                # Convert keys to lowercase for case-insensitive access
                row_lower = {k.lower(): v for k, v in row.items()}
                
                # Combine Description and Memo fields if they exist
                if 'description' in row_lower or 'memo' in row_lower:
                    description_parts = []
                    if row_lower.get('description', '').strip():
                        description_parts.append(row_lower.get('description', '').strip())
                    if row_lower.get('memo', '').strip():
                        description_parts.append(row_lower.get('memo', '').strip())
                    
                    combined_description = ' | '.join(description_parts) if description_parts else ''
                    
                    # Create a new row with the combined description
                    new_row = {k: v for k, v in row.items() if k.lower() not in ['description', 'memo']}
                    new_row['Description'] = combined_description
                    transactions.append(new_row)
                else:
                    # No description/memo fields to combine, use original row
                    transactions.append(dict(row))
            
            return transactions
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")

def read_chart_of_accounts(file_path: str) -> List[Dict[str, Any]]:
    """
    Read a chart of accounts file (TXT format only).
    """
    try:
        print(f"🔍 DEBUG: read_chart_of_accounts - Reading file: {file_path}")
        
        if not file_path.endswith('.txt'):
            raise ValueError("Chart of accounts file must be in TXT format")
            
        accounts = []
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            print(f"🔍 DEBUG: read_chart_of_accounts - TXT format, {len(lines)} lines to process")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if line and not line.startswith('#'):
                    # Try different separators: ': ' first, then ' - '
                    if ': ' in line:
                        parts = line.split(': ', 1)
                    elif ' - ' in line:
                        parts = line.split(' - ', 1)
                    else:
                        parts = []
                        print(f"🔍 DEBUG: Line {line_num}: No recognized separator in '{line}'")
                        
                    if len(parts) == 2:
                        account = {
                            'code': parts[0].strip(),
                            'name': parts[1].strip()
                        }
                        accounts.append(account)
                    elif line:  # Only warn for non-empty lines
                        print(f"🔍 DEBUG: Line {line_num}: Skipped malformed line '{line}'")
        
        print(f"🔍 DEBUG: read_chart_of_accounts - TXT parsing complete, created {len(accounts)} accounts")
        if accounts:
            print(f"🔍 DEBUG: Sample accounts: {accounts[0]} ... {accounts[-1]}")
        return accounts
    except FileNotFoundError:
        print(f"🔍 DEBUG: read_chart_of_accounts - ❌ File not found: {file_path}")
        raise FileNotFoundError(f"Chart of accounts file not found: {file_path}")
    except Exception as e:
        print(f"🔍 DEBUG: read_chart_of_accounts - ❌ Exception: {type(e).__name__}: {str(e)}")
        raise Exception(f"Error reading chart of accounts: {str(e)}")

def preprocess_chart_of_accounts(chart_of_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Preprocess chart of accounts for efficient usage.
    Creates lookup structures and categorized account lists.
    """
    # Create fast lookup dictionaries
    code_to_name = {}
    name_to_code = {}
    valid_codes = set()
    
    # Categorize accounts by type for smart filtering
    revenue_accounts = []
    expense_accounts = []
    asset_accounts = []
    liability_accounts = []
    equity_accounts = []
    
    for acc in chart_of_accounts:
        if not isinstance(acc, dict) or 'code' not in acc or 'name' not in acc:
            continue
            
        code = str(acc['code']).strip()
        name = str(acc['name']).strip()
        
        # Build lookup structures
        code_to_name[code] = name
        name_to_code[name] = code
        valid_codes.add(code)
        
        # Categorize by account type (first digit)
        first_digit = code[0] if code else '0'
        account_entry = f"{code}: {name}"
        
        if first_digit == '1':
            asset_accounts.append(account_entry)
        elif first_digit == '2':
            liability_accounts.append(account_entry)
        elif first_digit == '3':
            equity_accounts.append(account_entry)
        elif first_digit == '4':
            revenue_accounts.append(account_entry)
        elif first_digit in ['5', '6']:
            expense_accounts.append(account_entry)
    
    # Pre-format common COA text combinations
    all_accounts_text = "\n".join([f"{code}: {name}" for code, name in code_to_name.items()])
    revenue_text = "\n".join(revenue_accounts) if revenue_accounts else "No revenue accounts defined"
    expense_text = "\n".join(expense_accounts) if expense_accounts else "No expense accounts defined"
    balance_sheet_text = "\n".join(asset_accounts + liability_accounts + equity_accounts)
    
    return {
        'code_to_name': code_to_name,
        'name_to_code': name_to_code,
        'valid_codes': valid_codes,
        'all_accounts_text': all_accounts_text,
        'revenue_text': revenue_text,
        'expense_text': expense_text,
        'balance_sheet_text': balance_sheet_text,
        'revenue_accounts': revenue_accounts,
        'expense_accounts': expense_accounts,
        'asset_accounts': asset_accounts,
        'liability_accounts': liability_accounts,
        'equity_accounts': equity_accounts,
        'total_accounts': len(valid_codes)
    }

def validate_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate bank transaction data for required fields and formats.
    """
    required_fields = ['date', 'description', 'amount']
    errors = []
    warnings = []
    
    for i, transaction in enumerate(transactions):
        # Convert transaction keys to lowercase for case-insensitive checking
        transaction_lower = {k.lower(): v for k, v in transaction.items()}
        
        # Check required fields (case-insensitive)
        for field in required_fields:
            if field not in transaction_lower or not str(transaction_lower[field]).strip():
                errors.append(f"Row {i+1}: Missing required field '{field}'")
        
        # Validate amount is numeric
        try:
            amount_value = transaction_lower.get('amount', '0')
            float(str(amount_value).replace(',', '').replace('$', ''))
        except ValueError:
            errors.append(f"Row {i+1}: Invalid amount format")
            
        # Validate date format
        date_str = transaction_lower.get('date', '')
        if date_str:
            try:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
                    try:
                        datetime.strptime(str(date_str), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    warnings.append(f"Row {i+1}: Unusual date format '{date_str}'")
            except Exception:
                errors.append(f"Row {i+1}: Invalid date format")
    
    return {
        "valid": len(errors) == 0,
        "transaction_count": len(transactions),
        "errors": errors,
        "warnings": warnings
    }

def initialize_session_and_output_file(
    csv_file_path: str,
    chart_of_accounts_path: str,
    tool_context
) -> Dict[str, Any]:
    """
    Initialize the categorization session by loading transactions and chart of accounts,
    creating output file, and setting up session state.
    """
    try:
        print(f"🔍 DEBUG: initialize_session_and_output_file called")
        print(f"🔍 DEBUG: CSV file path: {csv_file_path}")
        print(f"🔍 DEBUG: COA file path: {chart_of_accounts_path}")
        
        # Generate session ID and file paths
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        output_file_path = f"data/output/categorization_results_{session_id}.jsonl"
        
        # Store the categorization session ID for later use by update functions
        tool_context.state["categorization.session_id"] = session_id
        
        # Load and validate files
        transactions = read_csv_file(csv_file_path)
        chart_of_accounts = read_chart_of_accounts(chart_of_accounts_path)
        
        validation = validate_transactions(transactions)
        if not validation['valid']:
            return {
                "status": "error",
                "error": "Transaction validation failed",
                "validation": validation
            }
        
        # Preprocess COA for efficient usage
        coa_processed = preprocess_chart_of_accounts(chart_of_accounts)
        print(f"🔍 DEBUG: COA preprocessed - {coa_processed['total_accounts']} accounts organized")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        # Add transaction IDs and create chunks
        for i, trans in enumerate(transactions):
            trans['transaction_id'] = f"trans_{i}"
        
        chunks = []
        for i in range(0, len(transactions), CHUNK_SIZE):
            chunk = transactions[i:i + CHUNK_SIZE]
            chunks.append({
                'chunk_number': len(chunks) + 1,
                'transactions': chunk,
                'start_index': i,
                'end_index': min(i + CHUNK_SIZE, len(transactions))
            })
        
        # Create empty output file with metadata header
        with open(output_file_path, 'w', encoding='utf-8') as f:
            # Write metadata as first line comment
            metadata = {
                "_metadata": {
                    "session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                    "csv_file_path": csv_file_path,
                    "chart_of_accounts_path": chart_of_accounts_path,
                    "total_transactions": len(transactions),
                    "total_chunks": len(chunks),
                    "total_coa_accounts": coa_processed['total_accounts']
                }
            }
            f.write(f"# {json.dumps(metadata)}\n")
        
        # Store in session state - now with preprocessed COA data
        tool_context.state["categorization.output_file"] = output_file_path
        tool_context.state["categorization.csv_file_path"] = csv_file_path
        tool_context.state["categorization.chart_accounts_path"] = chart_of_accounts_path
        tool_context.state["categorization.total_transactions"] = len(transactions)
        tool_context.state["categorization.total_chunks"] = len(chunks)
        tool_context.state["categorization.processed_chunks"] = 0
        tool_context.state["categorization.current_chunk"] = 0
        tool_context.state["categorization.chunks"] = chunks
        tool_context.state["categorization.chart_of_accounts"] = chart_of_accounts  # Keep original
        tool_context.state["categorization.coa_processed"] = coa_processed  # Add preprocessed data
        tool_context.state["categorization.status"] = "initialized"
        tool_context.state["categorization.created_at"] = datetime.now().isoformat()
        
        return {
            "status": "success",
            "session_id": session_id,
            "output_file": output_file_path,
            "total_transactions": len(transactions),
            "total_chunks": len(chunks),
            "total_coa_accounts": coa_processed['total_accounts'],
            "validation": validation
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Create FunctionTool instances
initialize_session_and_output_file_tool = FunctionTool(initialize_session_and_output_file) 