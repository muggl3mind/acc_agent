"""
Accounting Agent - Main agent orchestrating the accounting workflow
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define model constant following ADK patterns
MODEL_GEMINI_2_5_PRO = "gemini-2.5-pro"
MODEL = os.getenv("MODEL", MODEL_GEMINI_2_5_PRO)

# Import components
from .tools import (
    read_csv_file_tool, read_chart_of_accounts_tool, save_json_file_tool, save_csv_file_tool,
    validate_transactions_tool, format_categorization_results_tool, format_journal_entries_tool,
    chunk_transactions_tool
)
from .prompt import ROOT_AGENT_PROMPT
from .sub_agents.categorizer import categorizer_agent
from .sub_agents.journal_generator import journal_agent

# Workflow control tools (session management moved to categorizer)

def update_categorization_json(
    session_id: str,
    updates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Update specific categorizations in the JSONL file - BULLETPROOF DEBUG VERSION.
    
    Args:
        session_id: The categorization session ID
        updates: List of updates with transaction_id and new categorization data
        
    Returns:
        Update status and summary
    """
    print(f"🔍 ===== UPDATE_CATEGORIZATION_JSON DEBUG =====")
    print(f"🔍 CALLED WITH session_id: '{session_id}' (type: {type(session_id)})")
    print(f"🔍 CALLED WITH updates: {updates} (type: {type(updates)})")
    
    try:
        # List all files to see what actually exists
        output_dir = 'data/output/'
        if os.path.exists(output_dir):
            all_files = os.listdir(output_dir)
            cat_files = [f for f in all_files if 'categorization' in f]
            print(f"🔍 FILES IN OUTPUT DIR: {cat_files}")
        else:
            print(f"❌ OUTPUT DIRECTORY DOESN'T EXIST: {output_dir}")
            return {"status": "error", "error": f"Output directory not found: {output_dir}"}
        
        # Validate parameters
        if not isinstance(updates, list):
            error_msg = f"Updates parameter must be list, got {type(updates)}"
            print(f"❌ PARAM ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}
            
        if not updates:
            error_msg = "Updates list is empty"
            print(f"❌ PARAM ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}
        
        for i, update in enumerate(updates):
            if not isinstance(update, dict):
                error_msg = f"Update {i} must be dict, got {type(update)}"
                print(f"❌ PARAM ERROR: {error_msg}")
                return {"status": "error", "error": error_msg}
            print(f"🔍 UPDATE {i}: {update}")
        
        # Handle multiple possible session ID formats and file paths
        session_id_variants = [
            session_id,  # As provided
            session_id.replace('session_', ''),  # Remove session_ prefix if present
            f"session_{session_id}" if not session_id.startswith('session_') else session_id,  # Add session_ if missing
        ]
        
        possible_paths = []
        for sid in session_id_variants:
            possible_paths.extend([
                f'data/output/categorization_results_session_{sid}.jsonl',
                f'data/output/categorization_results_{sid}.jsonl',
                f'data/output/categorization_results_session_session_{sid}.jsonl'
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in possible_paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)
        
        print(f"🔍 TRYING PATHS: {unique_paths}")
        
        session_file = None
        for path in unique_paths:
            if os.path.exists(path):
                session_file = path
                print(f"✅ FOUND FILE: {path}")
                break
            else:
                print(f"❌ NOT FOUND: {path}")
        
        if not session_file:
            error_msg = f"NO CATEGORIZATION FILE FOUND. Tried paths: {unique_paths}"
            print(f"❌ FILE ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}
        
        # Test file reading step by step
        print(f"🔍 TESTING FILE READ: {session_file}")
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                first_100_chars = f.read(100)
            print(f"✅ FILE READ SUCCESS: {first_100_chars[:50]}...")
        except Exception as e:
            error_msg = f"FAILED TO READ FILE: {str(e)}"
            print(f"❌ FILE READ ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}
        
        # Load existing JSONL data
        print(f"🔍 PARSING JSONL DATA...")
        categorizations = []
        metadata = None
        line_count = 0
        
        with open(session_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('# '):
                    # Parse metadata
                    try:
                        metadata = json.loads(line[2:])
                        print(f"✅ PARSED METADATA: {metadata}")
                    except Exception as e:
                        print(f"⚠️  METADATA PARSE FAILED: {e}")
                else:
                    # Parse transaction
                    try:
                        transaction = json.loads(line)
                        categorizations.append(transaction)
                        line_count += 1
                        if line_count <= 3:  # Show first 3 transactions
                            print(f"✅ PARSED TRANSACTION {line_count}: {transaction.get('transaction_id', 'NO_ID')}")
                    except Exception as e:
                        print(f"⚠️  TRANSACTION PARSE FAILED line {line_num}: {e}")
        
        print(f"🔍 LOADED {len(categorizations)} TRANSACTIONS")
        
        if not categorizations:
            error_msg = "No transactions found in categorization file"
            print(f"❌ DATA ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}
        
        # Create update map for efficient lookup
        update_map = {u['transaction_id']: u for u in updates}
        print(f"🔍 UPDATE MAP: {update_map}")
        
        # Show existing transaction IDs to help debug
        existing_ids = [cat.get('transaction_id') for cat in categorizations[:5]]
        print(f"🔍 FIRST 5 EXISTING TRANSACTION IDs: {existing_ids}")
        
        # Update categorizations
        updated_count = 0
        for i, cat in enumerate(categorizations):
            trans_id = cat.get('transaction_id')
            if trans_id in update_map:
                # Update the categorization
                update = update_map[trans_id]
                old_account = f"{cat.get('account_code')} {cat.get('account_name', '')}"
                
                # Handle multiple nested data structures (AI behavior changes)
                if 'new_category' in update:
                    # New nested format: {'transaction_id': '...', 'new_category': {'account_code': '...', ...}}
                    new_cat = update['new_category']
                    new_account_code = new_cat.get('account_code', cat['account_code'])
                    new_account_name = new_cat.get('account_name', cat['account_name'])
                    new_confidence = new_cat.get('confidence', 0.95)
                    new_reasoning = new_cat.get('reasoning', 'User manually updated the category.')
                    print(f"🔍 USING NEW_CATEGORY FORMAT for {trans_id}")
                elif 'update_data' in update:
                    # Update data nested format: {'transaction_id': '...', 'update_data': {'account_code': '...', ...}}
                    update_data = update['update_data']
                    new_account_code = update_data.get('account_code', cat['account_code'])
                    new_account_name = update_data.get('account_name', cat['account_name'])
                    new_confidence = update_data.get('confidence', 0.95)
                    new_reasoning = update_data.get('reasoning', 'User manually updated the category.')
                    print(f"🔍 USING UPDATE_DATA FORMAT for {trans_id}")
                else:
                    # Old flat format: {'transaction_id': '...', 'account_code': '...', 'account_name': '...'}
                    new_account_code = update.get('account_code', cat['account_code'])
                    new_account_name = update.get('account_name', cat['account_name'])
                    new_confidence = update.get('confidence', 0.95)
                    new_reasoning = update.get('reasoning', 'User manually updated the category.')
                    print(f"🔍 USING FLAT FORMAT for {trans_id}")
                
                # Check if anything actually changed
                account_changed = (new_account_code != cat['account_code'] or new_account_name != cat.get('account_name', ''))
                
                if account_changed:
                    # Real update - apply all changes including metadata
                    categorizations[i].update({
                        'account_code': new_account_code,
                        'account_name': new_account_name,
                        'category': update.get('category', cat.get('category', 'Updated')),
                        'confidence': new_confidence,  # High confidence for manual updates
                        'reasoning': new_reasoning,
                        'updated_by': 'user',
                        'updated_at': datetime.now().isoformat()
                    })
                    new_account = f"{categorizations[i]['account_code']} {categorizations[i]['account_name']}"
                    print(f"✅ UPDATED {trans_id}: {old_account} → {new_account}")
                    updated_count += 1
                else:
                    # No real change - just log that user commented but didn't change categorization
                    print(f"ℹ️  NO CHANGE {trans_id}: User commented but account code/name unchanged ({old_account})")
                    # Don't increment updated_count or add update metadata
        
        print(f"🔍 UPDATED {updated_count} OF {len(updates)} REQUESTED TRANSACTIONS")
        
        # Recalculate confidence summary
        confidence_summary = {"high": 0, "medium": 0, "low": 0}
        for cat in categorizations:
            confidence = cat.get('confidence', 0)
            if confidence >= 0.9:
                confidence_summary['high'] += 1
            elif confidence >= 0.7:
                confidence_summary['medium'] += 1
            else:
                confidence_summary['low'] += 1
        
        # Test file writing
        print(f"🔍 TESTING FILE WRITE BACK...")
        try:
            # Write back to JSONL file
            with open(session_file, 'w', encoding='utf-8') as f:
                # Write metadata header if we have it
                if metadata:
                    f.write(f"# {json.dumps(metadata)}\n")
                
                # Write updated categorizations
                for cat in categorizations:
                    f.write(json.dumps(cat) + '\n')
            
            print(f"✅ FILE WRITE SUCCESS")
        except Exception as e:
            error_msg = f"FAILED TO WRITE FILE: {str(e)}"
            print(f"❌ FILE WRITE ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}
        
        print(f"🔍 ===== UPDATE COMPLETED SUCCESSFULLY =====")
        
        return {
            "status": "success",
            "updates_requested": len(updates),
            "updates_applied": updated_count,
            "confidence_summary": confidence_summary,
            "file_used": session_file,
            "ready_for_journal_entries": True
        }
        
    except Exception as e:
        error_msg = f"UNEXPECTED ERROR: {str(e)}"
        print(f"❌ CRITICAL ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": error_msg
        }

def load_categorization_results(session_id: str) -> Dict[str, Any]:
    """
    Load the categorization results from a JSONL file.
    
    Args:
        session_id: The categorization session ID
        
    Returns:
        Categorization results and status
    """
    try:
        session_file = f'data/output/categorization_results_session_{session_id}.jsonl'
        
        # Load JSONL data
        categorizations = []
        metadata = None
        
        with open(session_file, 'r', encoding='utf-8') as f:
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
                        categorizations.append(json.loads(line))
                    except:
                        pass
        
        # Calculate confidence summary
        confidence_summary = {"high": 0, "medium": 0, "low": 0}
        for cat in categorizations:
            confidence = cat.get('confidence', 0)
            if confidence >= 0.9:
                confidence_summary['high'] += 1
            elif confidence >= 0.7:
                confidence_summary['medium'] += 1
            else:
                confidence_summary['low'] += 1
        
        # Format low confidence items for review
        low_confidence = [
            cat for cat in categorizations
            if cat.get('confidence', 0) < 0.8
        ]
        
        # Reconstruct session data structure
        session_data = {
            'categorizations': categorizations,
            'confidence_summary': confidence_summary,
            'total_transactions': len(categorizations),
            'created_at': metadata.get('_metadata', {}).get('created_at') if metadata else None,
            'session_id': session_id
        }
        
        return {
            "status": "success",
            "session_data": session_data,
            "total_transactions": len(categorizations),
            "confidence_summary": confidence_summary,
            "low_confidence_items": low_confidence[:10],  # Show first 10 for review
            "has_low_confidence": len(low_confidence) > 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def finalize_categorization(
    session_id: str,
    output_file_path: Optional[str]
) -> Dict[str, Any]:
    """
    Finalize the categorization session and save to final JSON file.
    
    Args:
        session_id: The categorization session ID
        output_file_path: Optional custom path for output file
        
    Returns:
        Finalization status and file path
    """
    try:
        session_file = f'data/output/categorization_results_session_{session_id}.jsonl'
        
        if not output_file_path:
            output_file_path = f'data/output/{session_id}_final_categorization.json'
        
        # Load JSONL data
        categorizations = []
        metadata = None
        
        with open(session_file, 'r', encoding='utf-8') as f:
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
                        categorizations.append(json.loads(line))
                    except:
                        pass
        
        # Calculate confidence summary
        confidence_summary = {"high": 0, "medium": 0, "low": 0}
        for cat in categorizations:
            confidence = cat.get('confidence', 0)
            if confidence >= 0.9:
                confidence_summary['high'] += 1
            elif confidence >= 0.7:
                confidence_summary['medium'] += 1
            else:
                confidence_summary['low'] += 1
        
        # Prepare final output
        final_output = {
            "session_id": session_id,
            "created_at": metadata.get('_metadata', {}).get('created_at') if metadata else None,
            "finalized_at": datetime.now().isoformat(),
            "summary": {
                "total_transactions": len(categorizations),
                "confidence_distribution": confidence_summary,
                "categorization_complete": True
            },
            "categorized_transactions": categorizations
        }
        
        # Save to output file
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, 'w') as f:
            json.dump(final_output, f, indent=2)
        
        return {
            "status": "success",
            "output_file": output_file_path,
            "total_categorized": len(categorizations),
            "ready_for_journal_entries": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Create FunctionTool instances for workflow control
update_categorization_json_tool = FunctionTool(update_categorization_json)
load_categorization_results_tool = FunctionTool(load_categorization_results)
# finalize_categorization_tool = FunctionTool(finalize_categorization)  # No longer needed

# Initialize the root agent using ADK sub_agents pattern
root_agent = LlmAgent(
    model=MODEL,
    name="root_agent",
    tools=[
        # Workflow control tools
        update_categorization_json_tool,
        load_categorization_results_tool,
        # finalize_categorization_tool removed - journal_agent reads session state directly
    ],
    sub_agents=[categorizer_agent, 
                journal_agent],  
    instruction=ROOT_AGENT_PROMPT
)

if __name__ == "__main__":
    from google.adk.runners import run
    run(root_agent) 