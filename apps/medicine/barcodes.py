"""
Barcode/QR helpers used by the shelf-label print view. Generated on the fly
rather than stored, so a change to a medicine's code/barcode never leaves a
stale image on disk.
"""
import io

import barcode
import qrcode
from barcode.writer import SVGWriter


def generate_barcode_svg(value: str) -> str:
    """Returns inline SVG markup for a Code128 barcode of `value`."""
    buffer = io.BytesIO()
    code128 = barcode.get("code128", value, writer=SVGWriter())
    code128.write(buffer, options={"write_text": False, "module_height": 12, "quiet_zone": 2})
    return buffer.getvalue().decode("utf-8")


def generate_qr_data_uri(value: str) -> str:
    """Returns a base64 data: URI for a QR code PNG encoding `value`
    (used to let a phone camera jump straight to the medicine's detail page)."""
    import base64

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
