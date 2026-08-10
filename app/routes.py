from PIL import Image
from flask import Blueprint, current_app, render_template, request, jsonify

from .printer import PrinterQueue, PrinterOffline

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
