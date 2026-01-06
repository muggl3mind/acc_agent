---
description: Analyze confidence scores from the latest classification results
---

Analyze the confidence scores from the most recent transaction classification run.

Please perform the following analysis:

1. Find the most recent classification results file:
   ```bash
   ls -lt data/output/classification_results_*.jsonl 2>/dev/null | head -1
   ```

2. Read the file and calculate:
   - Total number of transactions
   - Number and percentage of high confidence (90-100%)
   - Number and percentage of medium confidence (70-89%)
   - Number and percentage of low confidence (<70%)
   - Average confidence score

3. List all transactions with confidence < 70% showing:
   - Transaction ID
   - Description
   - Account code/name
   - Confidence score
   - Reasoning

4. Show which accounts were used most frequently

5. Provide actionable recommendations for improving low-confidence classifications
