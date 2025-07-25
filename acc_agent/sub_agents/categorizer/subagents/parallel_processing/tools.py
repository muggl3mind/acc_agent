"""
Tools for the Parallel Processing subagent (ThreadPoolExecutor-based parallel processing)
"""

import concurrent.futures
import os
import json
from typing import Dict, List, Any
from datetime import datetime
import google.generativeai as genai
from google.adk.tools import FunctionTool

def validate_account_code(account_code: str, valid_codes: set, code_to_name: dict) -> dict:
    """
    Validate and clean account code against the user's Chart of Accounts.
    Returns corrected account info or defaults to Other Expenses.
    """
    if not account_code or not isinstance(account_code, str):
        return {
            'account_code': '6900',
            'account_name': code_to_name.get('6900', 'Other Expenses'),
            'validation_note': 'Empty or invalid account code provided'
        }
    
    # Clean the code (remove whitespace, ensure string)
    clean_code = str(account_code).strip()
    
    # Check if code exists in user's COA
    if clean_code in valid_codes:
        return {
            'account_code': clean_code,
            'account_name': code_to_name[clean_code],
            'validation_note': None
        }
    
    # Code not found in COA - default to Other Expenses
    return {
        'account_code': '6900',
        'account_name': code_to_name.get('6900', 'Other Expenses'),
        'validation_note': f'Account code {clean_code} not found in Chart of Accounts. Defaulted to Other Expenses.'
    }

def get_relevant_coa_text(amount: float, coa_processed: dict) -> str:
    """
    Return relevant COA accounts based on transaction amount to reduce token usage.
    """
    try:
        amount_float = float(str(amount).replace(',', '').replace('$', ''))
    except (ValueError, TypeError):
        amount_float = 0
    
    if amount_float > 0:
        # Positive amounts - likely revenue, refunds, or deposits
        relevant_text = "REVENUE ACCOUNTS:\n" + coa_processed['revenue_text'] + "\n\n"
        relevant_text += "BALANCE SHEET ACCOUNTS (for transfers/capital):\n" + coa_processed['balance_sheet_text']
    else:
        # Negative amounts - expenses, purchases, payments
        relevant_text = "EXPENSE ACCOUNTS:\n" + coa_processed['expense_text'] + "\n\n"
        relevant_text += "BALANCE SHEET ACCOUNTS (for asset purchases/loan payments):\n" + coa_processed['balance_sheet_text']
    
    return relevant_text

def categorize_single_chunk_sync(
    chunk_index: int,
    chunk_data: Dict[str, Any], 
    coa_processed: Dict[str, Any],
    total_chunks: int
) -> List[Dict[str, Any]]:
    """
    Categorize a single chunk synchronously using threading with optimized COA handling.
    """
    try:
        print(f"📦 Processing chunk {chunk_index + 1}/{total_chunks} in parallel...")
        
        chunk_transactions = chunk_data['transactions']
        valid_codes = coa_processed['valid_codes']
        code_to_name = coa_processed['code_to_name']
        
        # Format transactions for LLM
        transactions_text = ""
        for i, trans in enumerate(chunk_transactions, 1):
            amount = trans.get('amount', trans.get('Amount', 0))
            transactions_text += f"{i}. ID: {trans.get('transaction_id', '')}\n"
            transactions_text += f"   Date: {trans.get('date', trans.get('Date', ''))}\n"
            transactions_text += f"   Description: {trans.get('description', trans.get('Description', ''))}\n"
            transactions_text += f"   Amount: {amount}\n\n"
        
        # Get relevant COA based on transaction types in this chunk
        # For simplicity, use all accounts but note this could be optimized further
        chart_text = coa_processed['all_accounts_text']
        
        # Create the improved categorization prompt
        categorization_prompt = f"""You are an expert accounting categorization AI. Analyze each transaction and categorize it using ONLY the provided Chart of Accounts.

CHART OF ACCOUNTS (USE ONLY THESE CODES):
{chart_text}

TRANSACTIONS TO CATEGORIZE:
{transactions_text}

CRITICAL REQUIREMENTS:
1. You MUST use ONLY account codes that exist in the Chart of Accounts above
2. You MUST NOT create or invent new account codes
3. If uncertain about the best match, use account code 6900 (Other Expenses) and indicate low confidence
4. Account codes must exactly match those in the Chart of Accounts

For each transaction, provide:
1. account_code: MUST be from the Chart of Accounts above
2. account_name: MUST match the name from the Chart of Accounts  
3. confidence: Score from 0.0 to 1.0 based on certainty
4. reasoning: Brief explanation for your categorization choice

CONFIDENCE SCORING:
- 0.9-1.0: Very clear match (obvious categorization)
- 0.7-0.89: Good match (likely correct but some uncertainty)  
- 0.5-0.69: Uncertain match (needs human review)
- Below 0.5: Very uncertain (definitely needs review)

CATEGORIZATION GUIDELINES:
- Positive amounts: Usually revenue, refunds, loans, or capital contributions
- Negative amounts: Usually expenses, purchases, payments, or transfers
- Look for keywords in descriptions to match appropriate expense categories
- When in doubt, use 6900 (Other Expenses) with low confidence for manual review

Return ONLY a JSON array with this exact format:
[
  {{
    "transaction_id": "trans_0",
    "account_code": "5100", 
    "account_name": "Salaries and Wages Expense",
    "confidence": 0.95,
    "reasoning": "Description 'PAYROLL RUN' clearly indicates salary expense"
  }},
  ...
]"""
        
        # Initialize model (each thread gets its own model instance)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        
        # Make synchronous API call
        response = model.generate_content(categorization_prompt)
        response_text = response.text.strip()
        
        # Parse JSON response
        if response_text.startswith('```json'):
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif response_text.startswith('```'):
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        try:
            categorizations = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback for failed JSON parsing
            print(f"❌ JSON parsing failed for chunk {chunk_index + 1}")
            categorizations = []
            for trans in chunk_transactions:
                categorizations.append({
                    "transaction_id": trans.get('transaction_id', ''),
                    "account_code": "6900",
                    "account_name": code_to_name.get("6900", "Other Expenses"),
                    "confidence": 0.3,
                    "reasoning": "JSON parsing failed, using fallback categorization"
                })
        
        # Validate and merge results with transaction data
        categorized_transactions = []
        validation_errors = 0
        
        for i, trans in enumerate(chunk_transactions):
            cat = categorizations[i] if i < len(categorizations) else {
                "account_code": "6900",
                "account_name": code_to_name.get("6900", "Other Expenses"),
                "confidence": 0.3,
                "reasoning": "Missing categorization result"
            }
            
            # Validate the account code against user's COA
            validated_account = validate_account_code(
                cat.get('account_code'), 
                valid_codes, 
                code_to_name
            )
            
            # Track validation corrections
            if validated_account['validation_note']:
                validation_errors += 1
                original_reasoning = cat.get('reasoning', 'No reasoning provided')
                corrected_reasoning = f"{original_reasoning} | CORRECTED: {validated_account['validation_note']}"
            else:
                corrected_reasoning = cat.get('reasoning', 'No reasoning provided')
            
            categorized_transaction = {
                'transaction_id': trans.get('transaction_id', ''),
                'date': trans.get('date', trans.get('Date', '')),
                'description': trans.get('description', trans.get('Description', '')),
                'amount': trans.get('amount', trans.get('Amount', 0)),
                'account_code': validated_account['account_code'],
                'account_name': validated_account['account_name'],
                'confidence': float(cat.get('confidence', 0.3)),
                'reasoning': corrected_reasoning
            }
            categorized_transactions.append(categorized_transaction)
        
        if validation_errors > 0:
            print(f"⚠️  Chunk {chunk_index + 1}: {validation_errors} account codes corrected to match COA")
        
        print(f"✅ Chunk {chunk_index + 1} completed: {len(categorized_transactions)} transactions")
        return categorized_transactions
        
    except Exception as e:
        print(f"❌ Chunk {chunk_index + 1} failed: {str(e)}")
        # Return error transactions for this chunk
        error_transactions = []
        chunk_transactions = chunk_data.get('transactions', [])
        coa_processed = coa_processed or {}
        code_to_name = coa_processed.get('code_to_name', {})
        
        for trans in chunk_transactions:
            error_transactions.append({
                'transaction_id': trans.get('transaction_id', 'error'),
                'date': trans.get('date', trans.get('Date', '')),
                'description': trans.get('description', trans.get('Description', '')),
                'amount': trans.get('amount', trans.get('Amount', 0)),
                'account_code': '6900',
                'account_name': code_to_name.get('6900', 'Other Expenses'),
                'confidence': 0.0,
                'reasoning': f'Parallel processing failed: {str(e)}'
            })
        return error_transactions

def process_all_chunks_parallel(tool_context) -> Dict[str, Any]:
    """
    Process all chunks in parallel using ThreadPoolExecutor with optimized COA handling.
    This is used by ParallelProcessingAgent.
    """
    try:
        print(f"🚀 Starting parallel chunk processing workflow...")
        
        # Get chunks and preprocessed COA data from session state
        chunks = tool_context.state.get("categorization.chunks", [])
        coa_processed = tool_context.state.get("categorization.coa_processed", {})
        output_file = tool_context.state.get("categorization.output_file")
        
        if not chunks:
            return {
                "status": "error",
                "error": "No chunks found in session state"
            }
        
        if not coa_processed or not coa_processed.get('valid_codes'):
            return {
                "status": "error", 
                "error": "No preprocessed Chart of Accounts data found in session state"
            }
        
        print(f"📊 Processing {len(chunks)} chunks with {coa_processed['total_accounts']} COA accounts...")
        print(f"🔍 COA validation enabled: Only valid account codes will be used")
        
        # Configure Gemini API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "error": "GOOGLE_API_KEY environment variable not set"
            }
        
        genai.configure(api_key=api_key)
        
        # Use ThreadPoolExecutor for parallel processing
        start_time = datetime.now()
        
        print(f"🚀 Launching {len(chunks)} parallel categorization tasks...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            # Submit all chunks for parallel processing (now with COA validation)
            future_to_chunk = {
                executor.submit(
                    categorize_single_chunk_sync,
                    i, 
                    chunk, 
                    coa_processed,  # Pass preprocessed COA data instead of raw text
                    len(chunks)
                ): i for i, chunk in enumerate(chunks)
            }
            
            # Collect results as they complete
            results = [None] * len(chunks)  # Preserve order
            successful_chunks = 0
            failed_chunks = []
            total_validation_corrections = 0
            
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    result = future.result()
                    results[chunk_index] = result
                    successful_chunks += 1
                    
                    # Count validation corrections
                    for trans in result:
                        if 'CORRECTED:' in trans.get('reasoning', ''):
                            total_validation_corrections += 1
                            
                except Exception as e:
                    print(f"❌ Chunk {chunk_index + 1} raised exception: {e}")
                    failed_chunks.append(chunk_index + 1)
                    # Create error result for this chunk
                    error_transactions = []
                    chunk_transactions = chunks[chunk_index].get('transactions', [])
                    code_to_name = coa_processed.get('code_to_name', {})
                    
                    for trans in chunk_transactions:
                        error_transactions.append({
                            'transaction_id': trans.get('transaction_id', 'error'),
                            'date': trans.get('date', trans.get('Date', '')),
                            'description': trans.get('description', trans.get('Description', '')),
                            'amount': trans.get('amount', trans.get('Amount', 0)),
                            'account_code': '6900',
                            'account_name': code_to_name.get('6900', 'Other Expenses'),
                            'confidence': 0.0,
                            'reasoning': f'Thread execution failed: {str(e)}'
                        })
                    results[chunk_index] = error_transactions
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"🎉 Parallel processing complete!")
        print(f"⏱️  Processing time: {processing_time:.1f} seconds ({processing_time/60:.1f} minutes)")
        print(f"✅ Successful chunks: {successful_chunks}/{len(chunks)}")
        if failed_chunks:
            print(f"❌ Failed chunks: {failed_chunks}")
        if total_validation_corrections > 0:
            print(f"🔧 Total account codes corrected to match COA: {total_validation_corrections}")
        
        # Append all results to file sequentially (to avoid race conditions)
        print(f"💾 Writing all results to file: {output_file}")
        total_transactions = 0
        
        with open(output_file, 'a', encoding='utf-8') as f:
            for chunk_index, chunk_results in enumerate(results):
                if chunk_results:  # Skip None results
                    for transaction in chunk_results:
                        # Ensure consistent format
                        standardized_result = {
                            "transaction_id": transaction.get('transaction_id', ''),
                            "date": transaction.get('date', ''),
                            "description": transaction.get('description', ''),
                            "amount": transaction.get('amount', 0),
                            "account_code": transaction.get('account_code', ''),
                            "account_name": transaction.get('account_name', ''),
                            "confidence": transaction.get('confidence', 0.0),
                            "reasoning": transaction.get('reasoning', ''),
                            "processed_at": datetime.now().isoformat(),
                            "chunk_number": chunk_index + 1
                        }
                        f.write(json.dumps(standardized_result) + '\n')
                        total_transactions += 1
        
        # Update session state
        tool_context.state["categorization.processed_chunks"] = len(chunks)
        tool_context.state["categorization.total_processed_transactions"] = total_transactions
        tool_context.state["categorization.validation_corrections"] = total_validation_corrections
        tool_context.state["categorization.processing_time_seconds"] = processing_time
        tool_context.state["categorization.status"] = "completed"
        
        return {
            "status": "success",
            "total_chunks_processed": successful_chunks,
            "total_transactions_processed": total_transactions,
            "failed_chunks": failed_chunks,
            "processing_time_seconds": processing_time,
            "processing_time_minutes": round(processing_time / 60, 1),
            "validation_corrections": total_validation_corrections,
            "coa_accounts_used": len(coa_processed['valid_codes']),
            "ready_for_filtering": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Create FunctionTool instances
process_all_chunks_parallel_tool = FunctionTool(process_all_chunks_parallel) 