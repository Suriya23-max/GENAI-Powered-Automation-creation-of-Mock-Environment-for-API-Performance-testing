import json
import os
import re
from flask import Flask, request, jsonify

APP = Flask(__name__)

# store endpoints globally so admin routes can inspect and modify them at runtime
MOCK_ENDPOINTS = {}



def load_collection(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def seg_to_flask(seg):
    # convert Postman-style {{var}} to Flask-style <var>
    m = re.match(r"^\{\{\s*(.*?)\s*\}\}$", seg)
    if m:
        name = m.group(1)
        # ensure valid flask variable name
        name = re.sub(r'[^0-9a-zA-Z_]', '_', name)
        return f"<{name}>"
    return seg


def path_from_url(url_obj):
    # Most entries provide a 'path' array; join them and convert tokens
    path_parts = url_obj.get('path') or []
    # Sometimes raw is just the urlPrefix; treat as root
    if not path_parts:
        return '/'
    converted = [seg_to_flask(p) for p in path_parts]
    return '/' + '/'.join(converted)


def collect_requests(items, endpoints):
    for item in items:
        if 'request' in item:
            req = item['request']
            method = (req.get('method') or 'GET').upper()
            url = req.get('url') or {}
            path = path_from_url(url)

            if path not in endpoints:
                endpoints[path] = {'methods': set(), 'examples': []}
            endpoints[path]['methods'].add(method)
            # store example body if present
            body = None
            if 'body' in req:
                b = req['body']
                if isinstance(b, dict):
                    raw = b.get('raw')
                    if raw:
                        try:
                            body = json.loads(raw)
                        except Exception:
                            body = raw
            endpoints[path]['examples'].append({'method': method, 'body': body, 'name': item.get('name')})

        # recurse into sub-items (folders)
        if 'item' in item and isinstance(item['item'], list):
            collect_requests(item['item'], endpoints)


def sanitize_endpoint_name(path):
    import re as _re
    return 'ep_' + _re.sub(r'[^0-9a-zA-Z]', '_', path)


def register_endpoints(app, endpoints):
    for path, data in endpoints.items():
        methods = list(data['methods'])

        def make_handler(p, examples, endpoint_name):
            def handler(**kwargs):
                # include path variables from URL, query params and JSON body
                resp = {
                    'mock': True,
                    'path': p,
                    'method': request.method,
                    'pathParams': kwargs,
                    'query': request.args.to_dict(flat=True),
                    'headers': {
                        'Authorization': request.headers.get('Authorization')
                    }
                }
                body = None
                try:
                    body = request.get_json(silent=True)
                except Exception:
                    body = None
                if body is None and request.data:
                    try:
                        body = json.loads(request.data.decode('utf-8'))
                    except Exception:
                        body = request.data.decode('utf-8', errors='ignore')

                resp['body'] = body

                # Attempt to return a canned fixture response if available.
                fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
                method_fixture = os.path.join(fixtures_dir, f"{endpoint_name}_{request.method}.json")
                generic_fixture = os.path.join(fixtures_dir, f"{endpoint_name}.json")

                for fixture_path in (method_fixture, generic_fixture):
                    if os.path.exists(fixture_path):
                        try:
                            with open(fixture_path, 'r', encoding='utf-8') as fh:
                                fixture = json.load(fh)
                            # fixture may be either {'status': int, 'body': {...}} or a raw body object
                            if isinstance(fixture, dict) and 'status' in fixture and 'body' in fixture:
                                status = int(fixture.get('status', 200))
                                return jsonify(fixture['body']), status
                            else:
                                # return fixture as body with 200/201 default
                                status = 201 if request.method == 'POST' else 200
                                return jsonify(fixture), status
                        except Exception:
                            # fall back to default behavior if fixture load fails
                            break

                # Provide a lightweight example-driven response if available (fallback)
                example = None
                for ex in examples:
                    if ex['method'] == request.method:
                        example = ex
                        break
                if example and example.get('body') is not None:
                    ex_body = example['body']
                    if isinstance(ex_body, dict):
                        stub = {k: (v if not isinstance(v, str) else v) for k, v in ex_body.items()}
                        resp['example'] = stub

                status = 200
                if request.method == 'POST':
                    status = 201
                if request.method == 'DELETE':
                    status = 204
                return jsonify(resp), status

            return handler

        # Register route once with all methods
        endpoint_name = 'ep_' + re.sub(r'[^0-9a-zA-Z]', '_', path)
        handler = make_handler(path, data['examples'], endpoint_name)
        # Flask doesn't allow registering the exact same function name multiple times,
        # so set a unique endpoint name based on the path
        app.add_url_rule(path, endpoint=endpoint_name, view_func=handler, methods=methods)


@APP.route('/__mock_endpoints', methods=['GET'])
def mock_endpoints():
    # Return a list of registered templates and allowed methods
    eps = APP.config.get('MOCK_ENDPOINTS', {})
    out = []
    for path, data in eps.items():
        out.append({'path': path, 'methods': sorted(list(data.get('methods', [])))} )
    return jsonify({'endpoints': out}), 200


@APP.errorhandler(405)
def handle_method_not_allowed(err):
    # Intercept Method Not Allowed errors. If the client attempted POST and a
    # fixture exists for that path (or an example is available), return it
    # instead of a 405. This avoids needing to register new url rules at runtime.
    try:
        path = request.path
        method = request.method
        if method != 'POST':
            return err

        endpoint_name = sanitize_endpoint_name(path)
        fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        method_fixture = os.path.join(fixtures_dir, f"{endpoint_name}_POST.json")
        generic_fixture = os.path.join(fixtures_dir, f"{endpoint_name}.json")
        for fixture_path in (method_fixture, generic_fixture):
            if os.path.exists(fixture_path):
                try:
                    with open(fixture_path, 'r', encoding='utf-8') as fh:
                        fixture = json.load(fh)
                    if isinstance(fixture, dict) and 'status' in fixture and 'body' in fixture:
                        return jsonify(fixture['body']), int(fixture.get('status', 201))
                    else:
                        return jsonify(fixture), 201
                except Exception:
                    break

        # fallback: echo request body
        body = None
        try:
            body = request.get_json(silent=True)
        except Exception:
            body = None
        if body is None and request.data:
            try:
                body = json.loads(request.data.decode('utf-8'))
            except Exception:
                body = request.data.decode('utf-8', errors='ignore')

        return jsonify({'mock': True, 'path': path, 'method': 'POST', 'body': body}), 201
    except Exception:
        return err


def main():
    base = os.path.dirname(__file__)
    coll_path = os.path.join(base, 'postman_collection.quickstreamapi.json')
    if not os.path.exists(coll_path):
        print('Postman collection file not found at', coll_path)
        return

    collection = load_collection(coll_path)
    items = collection.get('item', [])
    endpoints = {}
    collect_requests(items, endpoints)
    # store globally
    global MOCK_ENDPOINTS
    MOCK_ENDPOINTS = endpoints
    APP.config['MOCK_ENDPOINTS'] = MOCK_ENDPOINTS

    # Register collected endpoints
    register_endpoints(APP, endpoints)

    print(f'Registered {len(endpoints)} mock endpoints')
    APP.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()
