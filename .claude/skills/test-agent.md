---
description: Quick test the accounting agent with sample data
---

Run a full test of the accounting assistant agent using the sample data files.

Please execute the following test workflow:

1. Check that the required files exist:
   - `data/transactions/Sample Bank Export.csv`
   - `data/transactions/COA.txt`

2. Start the ADK web interface by running:
   ```bash
   adk web
   ```

3. Once the server starts, provide the user with this prompt to copy into the web interface:
   ```
   Classify the transactions at 'data/transactions/Sample Bank Export.csv'

   The Chart of Account is saved at 'data/transactions/COA.txt'

   Show the transaction_id for the flagged transactions
   ```

4. Let the user know the interface should be accessible at `http://localhost:8000`
