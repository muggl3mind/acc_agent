---
description: Run only the transaction classifier sub-agent for testing
---

Run just the transaction classification pipeline without generating journal entries.

This is useful for:
- Testing changes to the categorization logic
- Quickly checking classification accuracy
- Debugging the parallel processing workflow

Please execute:

1. Verify the environment is ready:
   - Check that GOOGLE_API_KEY is set
   - Verify input files exist

2. Run the classifier sub-agent:
   ```bash
   python -m acc_agent.sub_agents.categorizer.agent
   ```

3. After completion, show:
   - The session ID generated
   - Location of the classification results JSONL file
   - Summary of confidence scores
   - Any flagged transactions

4. Provide next steps:
   - How to view the results
   - How to run the journal generator with these results
   - How to update classifications if needed
