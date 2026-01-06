---
description: Clean up old output files, keeping only the most recent ones
---

Clean the data/output/ directory by removing old files while keeping the most recent ones.

Please do the following:

1. Show the user the current state:
   ```bash
   ls -lt data/output/ | head -20
   ```

2. Count the total number of files:
   - Classification results (*.jsonl)
   - Journal CSV files (*.csv)
   - Journal JSON files (*.json)

3. Ask the user how many of each file type they want to keep (default: 5 most recent)

4. After confirmation, remove old files keeping only the N most recent of each type:
   ```bash
   # Example for keeping 5 most recent
   cd data/output
   ls -t classification_results_*.jsonl | tail -n +6 | xargs rm -f
   ls -t journal_entries_*.csv | tail -n +6 | xargs rm -f
   ls -t journal_entries_*.json | tail -n +6 | xargs rm -f
   ```

5. Show the final state and disk space saved

**Safety**: Always confirm with the user before deleting files.
