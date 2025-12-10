"""
Generate fixtures (JSON canned responses) from the Postman collection.

For each endpoint that has an example request body in the Postman collection,
this script will write a fixture file under `fixtures/` named like:

  fixtures/ep__customers__post_POST.json

Format:
- If the example is a JSON object, the fixture will be written as:
  { "status": 201, "body": { ... } }

Run:
  & "C:/.../.venv/Scripts/python.exe" generate_fixtures.py
"""
import json
import os
import re


def sanitize_path_to_name(path):
    # produce same naming used in server: ep_ + non-alnum -> _
    return 'ep_' + re.sub(r'[^0-9a-zA-Z]', '_', path)


def seg_to_name(seg):
    m = re.match(r"^\{\{\s*(.*?)\s*\}\}$", seg)
    if m:
        name = m.group(1)
        return '{' + name + '}'
    return seg


def path_from_url(url_obj):
    path_parts = url_obj.get('path') or []
    if not path_parts:
        return '/'
    return '/' + '/'.join(path_parts)


def collect(items, results):
    for item in items:
        if 'request' in item:
            req = item['request']
            method = (req.get('method') or 'GET').upper()
            url = req.get('url') or {}
            path = path_from_url(url)
            body = None
            if 'body' in req and isinstance(req['body'], dict):
                raw = req['body'].get('raw')
                if raw:
                    try:
                        body = json.loads(raw)
                    except Exception:
                        body = None
            results.append((path, method, body, item.get('name')))
        if 'item' in item and isinstance(item['item'], list):
            collect(item['item'], results)


def main():
    here = os.path.dirname(__file__)
    coll = os.path.join(here, 'postman_collection.quickstreamapi.json')
    if not os.path.exists(coll):
        print('Collection file not found:', coll)
        return
    obj = json.load(open(coll, 'r', encoding='utf-8'))
    items = obj.get('item', [])
    results = []
    collect(items, results)

    fixtures_dir = os.path.join(here, 'fixtures')
    os.makedirs(fixtures_dir, exist_ok=True)

    created = 0
    for path, method, body, name in results:
        if body is None:
            continue
        endpoint_name = sanitize_path_to_name(path)
        filename = f"{endpoint_name}_{method}.json"
        path_out = os.path.join(fixtures_dir, filename)
        # default status code
        status = 201 if method == 'POST' else 200
        content = {'status': status, 'body': body}
        try:
            with open(path_out, 'w', encoding='utf-8') as fh:
                json.dump(content, fh, indent=2)
            created += 1
        except Exception as e:
            print('Failed to write', path_out, e)

    print(f'Wrote {created} fixtures to', fixtures_dir)


if __name__ == '__main__':
    main()
