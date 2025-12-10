# Quickstream Mock Server

This mock server reads the Postman collection `postman_collection.quickstreamapi.json` (located in the same folder) and dynamically registers endpoints described by the collection.

Prerequisites
- Python 3.8+
- Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the server

```powershell
python mock_server.py
```

The server listens on port `5000`. Registered routes are printed to the console when the server starts.

Notes
- Path template tokens like `{{customerId}}` are converted to Flask path params like `<customerId>`.
- Responses are basic JSON stubs echoing request data and a small example body when available from the collection.

Quick test (PowerShell)

```powershell
# create venv (optional)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# run mock server on default port 5000
python mock_server.py

# test an endpoint (example)
Invoke-RestMethod -Method Get -Uri "http://localhost:5000/customers/12345/accounts"
```
