#!/usr/bin/env python
import argparse

from app import create_app


def main():
    parser = argparse.ArgumentParser(description="LabelSmith — label designer for Brother QL printers")
    parser.add_argument('--model', default='QL-700', help='Printer model (default: QL-700)')
    parser.add_argument('--label-size', default='62', help='Label size, e.g. 62 (default: 62)')
    parser.add_argument('--port', type=int, default=8014, help='HTTP port (default: 8014)')
    parser.add_argument('printer', help='Device specifier, e.g. file:///dev/usb/lp0')
    args = parser.parse_args()

    app = create_app({
        'PRINTER_MODEL': args.model,
        'PRINTER_DEVICE': args.printer,
        'LABEL_SIZE': args.label_size,
    })
    app.run(host='0.0.0.0', port=args.port)


if __name__ == '__main__':
    main()
