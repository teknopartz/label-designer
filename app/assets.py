import json
import os
import re
import urllib.request

FONTS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'fonts', 'google')
ICONS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'icons')
MANIFEST_PATH = os.path.join(FONTS_DIR, 'manifest.json')

# Metadata/search only — the actual font bytes still come straight from
# Google's own fonts.gstatic.com CDN, same as a normal <link> to Google Fonts.
GWFH_LIST_URL = 'https://gwfh.mranftl.com/api/fonts'
GWFH_FAMILY_URL = 'https://gwfh.mranftl.com/api/fonts/{id}?subsets=latin'

ICON_CODEPOINTS_URL = (
    'https://raw.githubusercontent.com/google/material-design-icons/master/'
    'variablefont/MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D.codepoints'
)
ICON_SVG_URL = (
    'https://raw.githubusercontent.com/google/material-design-icons/master/'
    'symbols/web/{name}/materialsymbolsoutlined/{name}_24px.svg'
)
# Same repo's own version-tracking file, keyed "category::icon_name" — the
# official taxonomy (18 real categories, plus an uncategorized "symbols"
# catch-all we ignore). Separate from the codepoints file above, which is
# just a flat name list with no grouping.
ICON_VERSIONS_URL = (
    'https://raw.githubusercontent.com/google/material-design-icons/master/'
    'update/current_versions.json'
)
ICON_CATEGORY_LABELS = {
    'action': 'Actions', 'alert': 'Alerts', 'av': 'Audio & Video',
    'communication': 'Communication', 'content': 'Content', 'device': 'Devices',
    'editor': 'Editor', 'file': 'Files', 'hardware': 'Hardware', 'home': 'Home',
    'image': 'Images & Camera', 'maps': 'Maps', 'navigation': 'Navigation',
    'notification': 'Notifications', 'places': 'Places', 'search': 'Search',
    'social': 'People & Social', 'toggle': 'Toggles',
}

_font_list_cache = None
_icon_name_cache = None
_icon_categories_cache = None  # {category: [icon names]}

# Google Fonts variant id -> (weight, style) pair we register as a webfont.
# Matches the same normal/bold/italic/bold-italic set used for DejaVu Sans,
# so the existing bold/italic checkboxes work unchanged for any new font.
VARIANT_MAP = {
    'regular': 'normal_normal',
    '700': 'bold_normal',
    'italic': 'normal_italic',
    '700italic': 'bold_italic',
}


def _fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'label-designer'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode('utf-8'))


def _fetch_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'label-designer'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read().decode('utf-8')


def search_fonts(query, limit=20):
    global _font_list_cache
    if _font_list_cache is None:
        _font_list_cache = _fetch_json(GWFH_LIST_URL)
    q = query.lower()
    matches = [f for f in _font_list_cache if q in f['family'].lower()]
    return [{'id': f['id'], 'family': f['family'], 'category': f['category']} for f in matches[:limit]]


def _load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def _save_manifest(manifest):
    os.makedirs(FONTS_DIR, exist_ok=True)
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2)


def installed_fonts():
    return _load_manifest()


def install_font(font_id):
    manifest = _load_manifest()
    if font_id in manifest:
        return manifest[font_id]

    data = _fetch_json(GWFH_FAMILY_URL.format(id=font_id))
    family = data['family']
    family_dir = os.path.join(FONTS_DIR, font_id)
    os.makedirs(family_dir, exist_ok=True)

    variants_by_id = {v['id']: v for v in data['variants']}
    saved = {}
    for variant_id, key in VARIANT_MAP.items():
        variant = variants_by_id.get(variant_id)
        if not variant or 'woff2' not in variant:
            continue
        filename = f'{key}.woff2'
        dest = os.path.join(family_dir, filename)
        urllib.request.urlretrieve(variant['woff2'], dest)
        saved[key] = f'/static/fonts/google/{font_id}/{filename}'

    manifest[font_id] = {'family': family, 'files': saved}
    _save_manifest(manifest)
    return manifest[font_id]


def _ensure_icon_names_loaded():
    global _icon_name_cache
    if _icon_name_cache is None:
        text = _fetch_text(ICON_CODEPOINTS_URL)
        _icon_name_cache = {line.split()[0] for line in text.strip().splitlines() if line.strip()}
    return _icon_name_cache


def search_icons(query, limit=30):
    names = _ensure_icon_names_loaded()
    q = query.lower().replace(' ', '_')
    matches = sorted(n for n in names if q in n)
    return matches[:limit]


def _ensure_icon_categories_loaded():
    global _icon_categories_cache
    if _icon_categories_cache is not None:
        return _icon_categories_cache

    valid_names = _ensure_icon_names_loaded()
    data = _fetch_json(ICON_VERSIONS_URL)
    categories = {}
    for key in data.keys():
        category, name = key.split('::', 1)
        if category == 'symbols' or name not in valid_names:
            continue
        categories.setdefault(category, []).append(name)
    for names in categories.values():
        names.sort()
    _icon_categories_cache = categories
    return _icon_categories_cache


def list_icon_categories():
    categories = _ensure_icon_categories_loaded()
    return [
        {'id': cat, 'label': ICON_CATEGORY_LABELS.get(cat, cat.title()), 'count': len(names)}
        for cat, names in sorted(categories.items(), key=lambda kv: ICON_CATEGORY_LABELS.get(kv[0], kv[0]))
    ]


def icons_in_category(category, limit=200):
    categories = _ensure_icon_categories_loaded()
    return categories.get(category, [])[:limit]


def get_icon_svg_path(name):
    if not re.match(r'^[a-z0-9_]+$', name or ''):
        raise ValueError('invalid icon name')
    names = _ensure_icon_names_loaded()
    if name not in names:
        raise ValueError('unknown icon name')

    os.makedirs(ICONS_DIR, exist_ok=True)
    dest = os.path.join(ICONS_DIR, f'{name}.svg')
    if not os.path.exists(dest):
        urllib.request.urlretrieve(ICON_SVG_URL.format(name=name), dest)
    return dest
