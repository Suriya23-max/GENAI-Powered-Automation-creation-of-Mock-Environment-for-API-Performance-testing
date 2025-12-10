Fixtures directory for canned responses used by `server.py`.

Place JSON files named like `ep_<sanitised_path>_<HTTP_METHOD>.json`.

Examples:
- `ep__customers__post_POST.json` (method-specific)
- `ep__customers__post.json` (generic for any method)

Fixture formats supported:
- Raw JSON body -> returned with 200/201 default status.
- { "status": 201, "body": { ... } } -> explicit status and body.
