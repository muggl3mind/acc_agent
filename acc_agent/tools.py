"""
Tools for the accounting agent system
"""

import os
import csv
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from google.adk.tools import FunctionTool

# Configuration
CHUNK_SIZE = 20  # Transactions per chunk

# File operation tools
def read_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read a CSV file and return its contents as a list of dictionaries.
    Combines Description and Memo fields into a single Description field.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries representing the CSV data
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
    
    Args:
        file_path: Path to the chart of accounts TXT file
        
    Returns:
        List of dictionaries representing the chart of accounts
    """
    try:
        if not file_path.endswith('.txt'):
            raise ValueError("Chart of accounts file must be in TXT format")
            
        accounts = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Try different separators: ': ' first, then ' - '
                    if ': ' in line:
                        parts = line.split(': ', 1)
                    elif ' - ' in line:
                        parts = line.split(' - ', 1)
                    else:
                        parts = []
                        
                    if len(parts) == 2:
                        accounts.append({
                            'code': parts[0].strip(),
                            'name': parts[1].strip()
                        })
        return accounts
    except FileNotFoundError:
        raise FileNotFoundError(f"Chart of accounts file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading chart of accounts: {str(e)}")

def save_json_file(data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """
    Save data to a JSON file.
    
    Args:
        data: Dictionary data to save
        file_path: Path to save the file
        
    Returns:
        Status dictionary
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2)
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def save_csv_file(data: List[Dict[str, Any]], file_path: str) -> Dict[str, Any]:
    """
    Save data to a CSV file.
    
    Args:
        data: List of dictionaries to save
        file_path: Path to save the file
        
    Returns:
        Status dictionary
    """
    try:
        if not data:
            return {"status": "error", "error": "No data to save"}
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Data processing tools
def validate_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate bank transaction data for required fields and formats.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Dictionary with validation results
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

def format_categorization_results(categorized_data: Dict[str, Any]) -> str:
    """
    Format categorization results for user review.
    
    Args:
        categorized_data: Dictionary containing categorized transactions
        
    Returns:
        Formatted string for display
    """
    result = "## Transaction Categorization Results\n\n"
    
    transactions = categorized_data.get('transactions', [])
    summary = categorized_data.get('summary', {})
    
    # Summary section
    result += f"**Total Transactions:** {len(transactions)}\n"
    result += f"**Date Range:** {summary.get('date_range', 'N/A')}\n"
    result += f"**Total Amount:** ${summary.get('total_amount', 0):,.2f}\n\n"
    
    # Confidence distribution
    result += "### Confidence Distribution\n"
    confidence_dist = summary.get('confidence_distribution', {})
    for level, count in confidence_dist.items():
        result += f"- {level}: {count} transactions\n"
    result += "\n"
    
    # Low confidence transactions for review
    low_confidence = [t for t in transactions if t.get('confidence', 1.0) < 0.8]
    if low_confidence:
        result += "### Transactions Requiring Review (Confidence < 80%)\n\n"
        for trans in low_confidence[:10]:  # Show first 10
            result += f"**{trans['date']}** - {trans['description']}\n"
            result += f"  Amount: ${trans['amount']:,.2f}\n"
            result += f"  Category: {trans['category']} (Confidence: {trans['confidence']:.0%})\n"
            result += f"  Account: {trans['account_code']} - {trans['account_name']}\n\n"
            
        if len(low_confidence) > 10:
            result += f"*... and {len(low_confidence) - 10} more low-confidence transactions*\n"
    
    return result

def format_journal_entries(journal_entries: List[Dict[str, Any]]) -> str:
    """
    Format journal entries for user review.
    
    Args:
        journal_entries: List of journal entry dictionaries
        
    Returns:
        Formatted string for display
    """
    result = "## Journal Entries\n\n"
    
    # Group by date
    entries_by_date = {}
    for entry in journal_entries:
        date = entry.get('date', 'Unknown')
        if date not in entries_by_date:
            entries_by_date[date] = []
        entries_by_date[date].append(entry)
    
    # Format each date's entries
    for date in sorted(entries_by_date.keys()):
        result += f"### {date}\n\n"
        
        for entry in entries_by_date[date]:
            result += f"**Entry #{entry.get('entry_number', 'N/A')}** - {entry.get('description', 'No description')}\n"
            
            # Debits
            if entry.get('debit_amount', 0) > 0:
                result += f"  DR: {entry.get('debit_account', 'Unknown')} ${entry['debit_amount']:,.2f}\n"
                
            # Credits
            if entry.get('credit_amount', 0) > 0:
                result += f"  CR: {entry.get('credit_account', 'Unknown')} ${entry['credit_amount']:,.2f}\n"
                
            result += "\n"
    
    # Summary
    total_debits = sum(e.get('debit_amount', 0) for e in journal_entries)
    total_credits = sum(e.get('credit_amount', 0) for e in journal_entries)
    
    result += f"\n### Summary\n"
    result += f"- Total Entries: {len(journal_entries)}\n"
    result += f"- Total Debits: ${total_debits:,.2f}\n"
    result += f"- Total Credits: ${total_credits:,.2f}\n"
    result += f"- Balance: ${abs(total_debits - total_credits):,.2f} {'(Balanced)' if total_debits == total_credits else '(UNBALANCED)'}\n"
    
    return result



# Chunking tools
def chunk_transactions(
    transactions: List[Dict[str, Any]], 
    chunk_size: int
) -> List[List[Dict[str, Any]]]:
    """
    Split transactions into manageable chunks.
    
    Args:
        transactions: List of all transactions
        chunk_size: Number of transactions per chunk (typically 20)
        
    Returns:
        List of transaction chunks
    """
    # Use default chunk size if not provided or invalid
    if chunk_size <= 0:
        chunk_size = CHUNK_SIZE
        
    chunks = []
    for i in range(0, len(transactions), chunk_size):
        chunk = transactions[i:i + chunk_size]
        # Add transaction IDs for tracking
        for j, trans in enumerate(chunk):
            trans['transaction_id'] = f"trans_{i+j}"
        chunks.append(chunk)
    return chunks

# Create FunctionTool instances
read_csv_file_tool = FunctionTool(read_csv_file)
read_chart_of_accounts_tool = FunctionTool(read_chart_of_accounts)
save_json_file_tool = FunctionTool(save_json_file)
save_csv_file_tool = FunctionTool(save_csv_file)
validate_transactions_tool = FunctionTool(validate_transactions)
format_categorization_results_tool = FunctionTool(format_categorization_results)
format_journal_entries_tool = FunctionTool(format_journal_entries)

chunk_transactions_tool = FunctionTool(chunk_transactions) 