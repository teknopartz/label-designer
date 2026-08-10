import json
import os
import re

STORE_DIR = os.path.join(os.path.dirname(__file__), 'data', 'templates')


def _safe_filename(name):
    if not name or not re.match(r'^[A-Za-z0-9 _-]{1,60}$', name):
        raise ValueError('Template names can only use letters, numbers, spaces, - and _ (max 60 chars)')
    return name.strip() + '.json'


def list_templates():
    if not os.path.isdir(STORE_DIR):
        return []
    names = [f[:-5] for f in os.listdir(STORE_DIR) if f.endswith('.json')]
    return sorted(names, key=str.lower)


def load_template(name):
    path = os.path.join(STORE_DIR, _safe_filename(name))
    if not os.path.exists(path):
        raise FileNotFoundError(name)
    with open(path) as f:
        return json.load(f)


def save_template(name, data):
    os.makedirs(STORE_DIR, exist_ok=True)
    path = os.path.join(STORE_DIR, _safe_filename(name))
    with open(path, 'w') as f:
        json.dump(data, f)


def delete_template(name):
    path = os.path.join(STORE_DIR, _safe_filename(name))
    if os.path.exists(path):
        os.remove(path)
