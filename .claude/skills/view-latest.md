---
description: View the most recent journal entries and classification results
---

Find and display the contents of the most recent output files from the accounting agent.

Please do the following:

1. Find the most recent classification results file:
   ```bash
   ls -lt data/output/classification_results_*.jsonl 2>/dev/null | head -1
   ```

2. Find the most recent journal entries CSV:
   ```bash
   ls -lt data/output/journal_entries_*.csv 2>/dev/null | head -1
   ```

3. Find the most recent journal entries JSON:
   ```bash
   ls -lt data/output/journal_entries_*.json 2>/dev/null | head -1
   ```

4. Read and display a summary of each file:
   - For the JSONL file: Show the metadata and first 5 transactions
   - For the CSV file: Show the first 10 rows
   - For the JSON file: Show the summary section

5. Provide the full paths so the user can open them if needed.
