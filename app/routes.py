import io
import base64

from flask import Blueprint, current_app, render_template, request, jsonify

from .label import render_text_label
from .printer import PrinterQueue, PrinterOffline

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/api/print', methods=['POST'])
def print_label():
    text = (request.form.get('text') or '').strip()
    if not text:
        return jsonify(success=False, message="Nothing to print — enter some text first."), 400

    try:
        font_size = int(request.form.get('font_size', 60))
    except ValueError:
        font_size = 60

    img = render_text_label(text, font_size=font_size)

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


@bp.route('/api/preview', methods=['POST'])
def preview_label():
    text = (request.form.get('text') or '').strip()
    if not text:
        return jsonify(success=False, message="Nothing to preview"), 400

    try:
        font_size = int(request.form.get('font_size', 60))
    except ValueError:
        font_size = 60

    img = render_text_label(text, font_size=font_size)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return jsonify(success=True, image=f"data:image/png;base64,{b64}")
