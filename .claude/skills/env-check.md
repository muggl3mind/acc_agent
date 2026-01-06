---
description: Validate environment setup and dependencies
---

Verify that the accounting agent environment is properly configured and ready to run.

Please check the following:

## 1. Environment Variables
```bash
# Check if .env file exists
if [ -f .env ]; then
    echo "✓ .env file found"
    # Verify GOOGLE_API_KEY is set (don't display the key)
    if grep -q "GOOGLE_API_KEY" .env; then
        echo "✓ GOOGLE_API_KEY is configured"
    else
        echo "✗ GOOGLE_API_KEY not found in .env"
    fi
else
    echo "✗ .env file not found"
fi
```

## 2. Python Version
```bash
python --version
# Should be Python 3.13 or compatible
```

## 3. Required Dependencies
```bash
# Check if key packages are installed
python -c "import google.genai; print('✓ google-genai installed')" 2>/dev/null || echo "✗ google-genai not installed"
python -c "import adk; print('✓ ADK installed')" 2>/dev/null || echo "✗ ADK not installed"
```

## 4. Required Data Files
```bash
# Check for sample data
if [ -f "data/transactions/Sample Bank Export.csv" ]; then
    echo "✓ Sample bank export found"
else
    echo "✗ Sample bank export not found"
fi

if [ -f "data/transactions/COA.txt" ]; then
    echo "✓ Chart of Accounts found"
else
    echo "✗ Chart of Accounts not found"
fi
```

## 5. Output Directory
```bash
# Verify output directory exists and is writable
if [ -d "data/output" ] && [ -w "data/output" ]; then
    echo "✓ Output directory is ready"
else
    echo "⚠ Output directory may need to be created or has permission issues"
fi
```

## Summary
Provide a final checklist of what's working and what needs attention, with specific instructions for fixing any issues.
