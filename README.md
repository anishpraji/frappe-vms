# Visitor Management System for ERPNext

A complete visitor management module for Frappe / ERPNext — built for manufacturing factory environments.

## Features

- Visitor registration with photo & ID capture (webcam supported)
- Employee-driven approval workflow with email notifications
- QR code gate pass generation (thermal printer compatible)
- Check-in / check-out tracking with timestamps
- Visitor blacklist management
- Multi-gate support
- Script Reports with charts (Daily Summary, Overstayed, Department-wise)
- ERPNext Workspace with Number Cards dashboard
- Role-based permissions (Security Guard, Receptionist, HR Manager)

## Requirements

- ERPNext v14 or v15
- Frappe Framework v14+
- Python 3.10+

## Installation

```bash
# From your bench directory
bench get-app visitor_management https://github.com/yourusername/visitor_management.git

bench --site your-site.com install-app visitor_management

pip install qrcode[pil] Pillow

bench --site your-site.com migrate

bench build --app visitor_management

bench restart
```

## Roles

| Role | Permissions |
|------|-------------|
| Security Guard | Create, check-in, check-out |
| Receptionist | Full entry management |
| Employee | Approve/reject own visitors |
| HR Manager | View all, blacklist, reports |
| System Manager | Full access |

## License

MIT
