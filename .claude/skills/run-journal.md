---
description: Run only the journal entry generator sub-agent for testing
---

Run just the journal entry generation pipeline using existing classification results.

This is useful for:
- Testing changes to the journal generation logic
- Re-generating entries after updating classifications
- Debugging the double-entry bookkeeping workflow

Please execute:

1. Find the most recent classification results:
   ```bash
   ls -lt data/output/classification_results_*.jsonl 2>/dev/null | head -1
   ```

2. Verify the classification file is valid and contains transactions

3. Run the journal generator sub-agent:
   ```bash
   python -m acc_agent.sub_agents.journal_generator.agent
   ```

4. After completion, show:
   - Location of the generated CSV and JSON files
   - Summary statistics (total entries, total debits, total credits)
   - Confirmation that all entries balance
   - Any warnings or errors

5. Display a preview of the first few journal entries

6. Provide guidance on:
   - How to view the full output
   - How to import into accounting software
   - What modifications might be needed for their specific software
