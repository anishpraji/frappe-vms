import frappe


def get_qr_code_base64(data_str):
    try:
        import qrcode
        import base64
        from io import BytesIO
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(data_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return ""
