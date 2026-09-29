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

# Icons come from several open-licensed sets, all served through the Iconify
# API (one search/SVG endpoint for all of them). Each SVG is fetched once on
# first use and cached under ICONS_DIR, so a picked icon keeps working
# offline afterwards. Credits for each set are in the README.
ICONIFY_COLLECTION_URL = 'https://api.iconify.design/collection?prefix={prefix}'
# Icon data is fetched in bulk — every icon a category or search shows, in
# one request — because fetching each SVG separately gets rate-limited
# (HTTP 429) as soon as the picker shows a full page of results.
ICONIFY_ICONS_URL = 'https://api.iconify.design/{prefix}.json?icons={names}'
ICON_FETCH_CHUNK = 100  # icons per request, keeps the URL a sane length

ICON_SETS = {
    'game-icons': 'Clip art',                      # CC BY 3.0 — bold silhouettes
    'noto': 'Emoji',                               # Apache 2.0 — full colour
    'fluent-emoji-high-contrast': 'Emoji outline', # MIT — black line art
    'material-symbols': 'Symbols',                 # Apache 2.0
}

# game-icons.net ships 4000+ icons with no categories at all, so browsing
# uses these themes instead: an icon belongs to a theme if any word of its
# name (e.g. "sea-dragon" -> sea, dragon) is one of the theme's keywords.
GAME_ICON_THEMES = {
    'Monsters & Fantasy': 'dragon troll ogre goblin orc ghost skull witch wizard unicorn griffin kraken demon vampire zombie monster cyclops minotaur hydra fairy gargoyle werewolf mummy imp beast phoenix pegasus centaur golem spectre banshee elf dwarf giant',
    'Magic': 'potion wand spell crystal orb rune magic scroll cauldron pentacle tarot grimoire candle hat broom cards',
    'Animals': 'cat dog horse bird fish owl fox wolf bear rabbit frog snake turtle whale octopus spider bee butterfly elephant lion monkey pig cow sheep chicken duck deer mouse rat crab bat hedgehog squirrel snail dolphin penguin dinosaur tiger giraffe hippo koala sloth parrot eagle raven',
    'Sea': 'ship anchor boat wave shell shark whale octopus squid crab mermaid jellyfish seahorse coral submarine diving lighthouse trident fishing sailboat',
    'Space': 'rocket planet moon sun comet astronaut alien ufo satellite galaxy spaceship meteor asteroid earth star telescope',
    'Food & Drink': 'apple pear banana cheese bread cake pie pizza burger meat egg carrot tomato potato corn mushroom coffee tea wine beer bottle cup cookie candy grapes cherry lemon orange strawberry honey milk soup sandwich donut cupcake jar watermelon peach avocado',
    'Nature': 'tree flower leaf rose cactus pine oak palm sprout plant forest mountain cloud rain snowflake lightning rainbow tulip clover acorn seed sunflower',
    'Home & Tools': 'house hammer saw wrench key lock chair table lamp bed door broom bucket scissors needle toolbox shovel pliers screwdriver watering',
    'Sports & Games': 'ball soccer basketball tennis trophy medal dice chess card bowling golf ski bicycle skateboard kite puzzle joystick',
    'Vehicles': 'car truck bus train plane airplane motorcycle tractor helicopter bike',
    'Knights & Castles': 'sword shield helmet castle crown knight dagger bow arrow spear armor catapult tower',
}

_icon_collection_cache = {}  # prefix -> {category label: [icon names]}

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


FONT_CATEGORY_LABELS = {
    'sans-serif': 'Sans Serif', 'serif': 'Serif', 'display': 'Display',
    'handwriting': 'Handwriting', 'monospace': 'Monospace',
}


def _ensure_font_list_loaded():
    global _font_list_cache
    if _font_list_cache is None:
        _font_list_cache = _fetch_json(GWFH_LIST_URL)
    return _font_list_cache


def search_fonts(query='', category=None, limit=60):
    fonts = _ensure_font_list_loaded()
    q = (query or '').lower()
    matches = [
        f for f in fonts
        if q in f['family'].lower() and (category is None or f['category'] == category)
    ]
    return [{'id': f['id'], 'family': f['family'], 'category': f['category']} for f in matches[:limit]]


def list_font_categories():
    fonts = _ensure_font_list_loaded()
    counts = {}
    for f in fonts:
        counts[f['category']] = counts.get(f['category'], 0) + 1
    return [
        {'id': cat, 'label': FONT_CATEGORY_LABELS.get(cat, cat.title()), 'count': count}
        for cat, count in sorted(counts.items(), key=lambda kv: FONT_CATEGORY_LABELS.get(kv[0], kv[0]))
    ]


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
    # font_id becomes a directory name under FONTS_DIR, so reject anything
    # that isn't a plain google-webfonts-helper slug (e.g. "open-sans").
    if not re.match(r'^[a-z0-9-]{1,80}$', font_id or ''):
        raise ValueError('invalid font id')
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


def _is_wanted_icon(prefix, name):
    # Material Symbols lists every icon four more times as style variants,
    # and Noto every person emoji five more times in each skin tone — keep
    # just the base versions so browsing isn't a wall of near-duplicates.
    if prefix == 'material-symbols':
        return not name.endswith(('-rounded', '-sharp', '-outline'))
    if prefix == 'noto':
        return '-tone' not in name
    return True


def _icon_categories(prefix):
    if prefix not in ICON_SETS:
        raise ValueError('unknown icon set')
    if prefix in _icon_collection_cache:
        return _icon_collection_cache[prefix]

    data = _fetch_json(ICONIFY_COLLECTION_URL.format(prefix=prefix))
    if prefix == 'game-icons':
        names = sorted(data.get('uncategorized', []))
        categories = {}
        for label, keywords in GAME_ICON_THEMES.items():
            words = set(keywords.split())
            categories[label] = [n for n in names if words & set(n.split('-'))]
    else:
        categories = {
            label: sorted(n for n in members if _is_wanted_icon(prefix, n))
            for label, members in data.get('categories', {}).items()
        }
    categories = {label: names for label, names in categories.items() if names}
    _icon_collection_cache[prefix] = categories
    return categories


def _icon_names(prefix):
    return {n for names in _icon_categories(prefix).values() for n in names}


def _icon_svg(body, width, height):
    # Fixed 512px height so the SVG has real pixel dimensions — the editor
    # rasterises it at that size. Single-colour sets draw in currentColor,
    # which an <img> would leave black anyway; made explicit here.
    # Multi-colour emoji keep their own palette.
    body = body.replace('currentColor', '#000')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{512 * width / height:g}" height="512" '
        f'viewBox="0 0 {width} {height}">{body}</svg>'
    )


def _icon_cache_path(prefix, name):
    return os.path.join(ICONS_DIR, prefix, f'{name}.svg')


def _cache_icons(prefix, names):
    missing = [n for n in names if not os.path.exists(_icon_cache_path(prefix, n))]
    if not missing:
        return
    os.makedirs(os.path.join(ICONS_DIR, prefix), exist_ok=True)
    for i in range(0, len(missing), ICON_FETCH_CHUNK):
        chunk = missing[i:i + ICON_FETCH_CHUNK]
        data = _fetch_json(ICONIFY_ICONS_URL.format(prefix=prefix, names=','.join(chunk)))
        icons, aliases = data.get('icons', {}), data.get('aliases', {})
        for name in chunk:
            # An alias is just another name for an existing icon.
            icon = icons.get(name) or icons.get(aliases.get(name, {}).get('parent'))
            if not icon:
                continue
            svg = _icon_svg(
                icon['body'],
                icon.get('width', data.get('width', 16)),
                icon.get('height', data.get('height', 16)),
            )
            with open(_icon_cache_path(prefix, name), 'w') as f:
                f.write(svg)


def list_icon_sets():
    return [{'id': prefix, 'label': label} for prefix, label in ICON_SETS.items()]


def search_icons(prefix, query, limit=120):
    q = query.lower().strip().replace(' ', '-').replace('_', '-')
    names = _icon_names(prefix)
    # Whole-word matches first ("cat" -> cat, cat-face), then any substring
    # (catapult, caterpillar), each group alphabetical.
    word = sorted(n for n in names if q in n.split('-'))
    partial = sorted(n for n in names if q in n and q not in n.split('-'))
    results = (word + partial)[:limit]
    _cache_icons(prefix, results)
    return results


def list_icon_categories(prefix):
    return [
        {'id': label, 'label': label, 'count': len(names)}
        for label, names in _icon_categories(prefix).items()
    ]


def icons_in_category(prefix, category, limit=120):
    results = _icon_categories(prefix).get(category, [])[:limit]
    _cache_icons(prefix, results)
    return results


def get_icon_svg_path(prefix, name):
    if not re.match(r'^[a-z0-9-]+$', name or ''):
        raise ValueError('invalid icon name')
    if name not in _icon_names(prefix):
        raise ValueError('unknown icon name')

    _cache_icons(prefix, [name])
    path = _icon_cache_path(prefix, name)
    if not os.path.exists(path):
        raise ValueError('icon not available')
    return path
