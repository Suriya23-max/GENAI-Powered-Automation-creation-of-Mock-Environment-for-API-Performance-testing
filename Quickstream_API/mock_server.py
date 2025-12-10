from flask import Flask, request, jsonify, make_response
import os
import json
import re

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

app = Flask(__name__)


def load_fixtures():
    fixtures = {}
    if not os.path.isdir(FIXTURES_DIR):
        return fixtures
    for name in os.listdir(FIXTURES_DIR):
        if not name.lower().endswith('.json'):
            continue
        path = os.path.join(FIXTURES_DIR, name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                fixtures[name] = json.load(f)
        except Exception:
            # If file isn't valid JSON, store raw text
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    fixtures[name] = f.read()
            except Exception:
                fixtures[name] = None
    return fixtures


FIXTURES = load_fixtures()


def match_fixture_for_request(path: str, method: str):
    """Find the best-matching fixture file for a given request path and method.

    Strategy:
    - Split the incoming path into tokens (resource names).
    - For each fixture filename, count how many resource tokens appear in the filename.
    - Prefer fixtures that contain the HTTP method string (e.g., _POST, _GET) and
      have the highest match count.
    - Return the fixture content if found.
    """
    tokens = [t for t in path.split('/') if t]
    # Normalize tokens: skip ones that look like IDs (numeric or long hex-like)
    id_like = re.compile(r'^[0-9a-fA-F-]{3,}$')
    resource_tokens = [t for t in tokens if not id_like.match(t)]
    method_token = method.upper()

    best = None
    best_score = -1
    for fname, content in FIXTURES.items():
        lname = fname.lower()
        if method_token.lower() not in lname:
            continue
        score = 0
        for rt in resource_tokens:
            if rt.lower() in lname:
                score += 1
        if score > best_score:
            best_score = score
            best = (fname, content)

    return best


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
def mock(path):
    method = request.method
    # Find a fixture matching this request
    match = match_fixture_for_request(path, method)
    if match:
        fname, content = match
        # If content is dict/list, return JSON
        if isinstance(content, (dict, list)):
            resp = make_response(jsonify(content))
            resp.headers['X-Mock-Fixture'] = fname
            return resp
        # If content is raw text, return as plain text
        if isinstance(content, str):
            resp = make_response(content)
            resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
            resp.headers['X-Mock-Fixture'] = fname
            return resp

    # Default fallback response
    data = {
        "message": "mock response",
        "path": '/' + path,
        "method": method
    }
    resp = make_response(jsonify(data), 200)
    resp.headers['X-Mock-Fixture'] = 'none'
    return resp


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run a mock server for the Postman collection')
    parser.add_argument('--host', default='0.0.0.0', help='Host to listen on')
    parser.add_argument('--port', default=5000, type=int, help='Port to listen on')
    args = parser.parse_args()

    print(f"Loaded {len(FIXTURES)} fixtures from {FIXTURES_DIR}")
    app.run(host=args.host, port=args.port, debug=True)
