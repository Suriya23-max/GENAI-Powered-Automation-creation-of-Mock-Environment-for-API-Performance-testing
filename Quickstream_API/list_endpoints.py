"""
Generate runnable endpoint URLs from `postman_collection.quickstreamapi.json`.

Outputs:
- METHOD TEMPLATE_URL SAMPLE_URL

Run:
  & "C:/Users/Administrator/Downloads/Mock API creation/.venv/Scripts/python.exe" "C:/Users/Administrator/Downloads/Mock API creation/list_endpoints.py"
"""
import json
import os
import re

BASE = os.environ.get('MOCK_BASE', 'http://localhost:5000')


def seg_to_template(seg):
    m = re.match(r"^\{\{\s*(.*?)\s*\}\}$", seg)
    if m:
        name = m.group(1)
        return '{' + name + '}'
    return seg


def seg_to_sample(seg):
    m = re.match(r"^\{\{\s*(.*?)\s*\}\}$", seg)
    if m:
        name = m.group(1).lower()
        if 'id' in name or 'token' in name or 'number' in name or 'receipt' in name:
            return '12345'
        if 'date' in name:
            return '2025-12-02'
        if 'code' in name:
            return 'SAMPLE_CODE'
        return 'sample'
    return seg


def path_from_url(url_obj):
    path_parts = url_obj.get('path') or []
    if not path_parts:
        return '/', '/'
    templ_parts = [seg_to_template(p) for p in path_parts]
    sample_parts = [seg_to_sample(p) for p in path_parts]
    return '/' + '/'.join(templ_parts), '/' + '/'.join(sample_parts)


def collect(items, results):
    for item in items:
        if 'request' in item:
            req = item['request']
            method = (req.get('method') or 'GET').upper()
            url = req.get('url') or {}
            templ, sample = path_from_url(url)
            results.append((method, templ, sample, item.get('name')))
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

    # dedupe by method+template
    seen = set()
    out = []
    for method, templ, sample, name in results:
        key = (method, templ)
        if key in seen:
            continue
        seen.add(key)
        out.append((method, templ, sample, name))

    print('# Available endpoints (base = {})'.format(BASE))
    for method, templ, sample, name in out:
        templ_url = BASE.rstrip('/') + templ
        sample_url = BASE.rstrip('/') + sample
        print(f"{method:6} {templ_url}    # {name}")
        print(f"       sample: {method:6} {sample_url}")


if __name__ == '__main__':
    main()
