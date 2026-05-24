import frappe
import base64
from io import BytesIO


def get_qr_code_base64(data_str):
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(data_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        frappe.log_error(str(e), "QR Code Generation Error")
        return ""


def get_employee_dashboard_data(data):
    data["transactions"].append({
        "label": "Visitor Management",
        "items": ["Visitor Entry"]
    })
    return data
