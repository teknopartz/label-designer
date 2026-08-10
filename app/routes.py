from PIL import Image
from flask import Blueprint, current_app, render_template, request, jsonify, send_file

from .printer import PrinterQueue, PrinterOffline
from . import assets

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


def _load_uploaded_image():
    file = request.files.get('image')
    if file is None:
        return None, ("No image received", 400)
    try:
        img = Image.open(file.stream)
        img.load()
    except Exception:
        return None, ("Uploaded file isn't a valid image", 400)
    return img, None


@bp.route('/api/print', methods=['POST'])
def print_label():
    img, error = _load_uploaded_image()
    if error:
        message, status = error
        return jsonify(success=False, message=message), status

    printer = PrinterQueue(
        model=current_app.config['PRINTER_MODEL'],
        device_specifier=current_app.config['PRINTER_DEVICE'],
        label_size=current_app.config['LABEL_SIZE'],
    )

    if not printer.device_present():
        return jsonify(
            success=False,
            message="Printer not found — is it switched on?",
        ), 503

    printer.add_label_to_queue(img, count=1, cut=True)

    try:
        printer.process_queue()
    except PrinterOffline as e:
        return jsonify(success=False, message=str(e)), 503
    except Exception as e:
        current_app.logger.exception("Print failed")
        return jsonify(success=False, message=str(e)), 500

    return jsonify(success=True)


@bp.route('/api/fonts/search')
def fonts_search():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    try:
        return jsonify(assets.search_fonts(q))
    except Exception as e:
        current_app.logger.exception("Font search failed")
        return jsonify(error=str(e)), 502


@bp.route('/api/fonts/installed')
def fonts_installed():
    return jsonify(assets.installed_fonts())


@bp.route('/api/fonts/install', methods=['POST'])
def fonts_install():
    font_id = (request.get_json(silent=True) or {}).get('id') or request.form.get('id')
    if not font_id:
        return jsonify(error='missing id'), 400
    try:
        return jsonify(assets.install_font(font_id))
    except Exception as e:
        current_app.logger.exception("Font install failed")
        return jsonify(error=str(e)), 502


@bp.route('/api/icons/search')
def icons_search():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    try:
        return jsonify(assets.search_icons(q))
    except Exception as e:
        current_app.logger.exception("Icon search failed")
        return jsonify(error=str(e)), 502


@bp.route('/api/icons/<name>.svg')
def icon_svg(name):
    try:
        path = assets.get_icon_svg_path(name)
    except Exception as e:
        return jsonify(error=str(e)), 404
    return send_file(path, mimetype='image/svg+xml')
