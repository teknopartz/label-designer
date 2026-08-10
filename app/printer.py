import os

from brother_ql.backends import backend_factory, guess_backend
from brother_ql import BrotherQLRaster, create_label


class PrinterOffline(Exception):
    """Raised when the configured device node isn't present (printer off/disconnected)."""
    pass


class PrinterQueue:

    def __init__(self, model, device_specifier, label_size):
        self.model = model
        self.device_specifier = device_specifier
        self.label_size = label_size
        self._print_queue = []

        selected_backend = guess_backend(self.device_specifier)
        self._backend_class = backend_factory(selected_backend)['backend_class']

    def add_label_to_queue(self, image, count=1, cut=True):
        for _ in range(count):
            self._print_queue.append({'image': image, 'cut': cut})

    def device_present(self):
        # Only meaningful for file:// backends (our case: file:///dev/usb/lp0).
        if self.device_specifier.startswith('file://'):
            path = self.device_specifier[len('file://'):]
            return os.path.exists(path)
        return True

    def process_queue(self, dither=True):
        if not self.device_present():
            raise PrinterOffline(
                f"Printer device not found ({self.device_specifier}). "
                "Is the printer switched on?"
            )

        qlr = BrotherQLRaster(self.model)

        for entry in self._print_queue:
            create_label(
                qlr,
                entry['image'],
                self.label_size,
                dither=dither,
                cut=entry['cut'],
            )

        self._print_queue.clear()

        be = self._backend_class(self.device_specifier)
        be.write(qlr.data)
        be.dispose()
        del be
