# What Changed — "Default ERPNext UI" vs "Custom UI"

## The core difference

| Previous version | This version |
|---|---|
| Custom CSS mimicking ERPNext | **Zero custom CSS** — ERPNext's own stylesheet applies |
| Custom HTML shells for navbar, sidebar | **Native Frappe layout** — ERPNext renders these automatically from DocType JSON |
| Custom status badges | **`frm.page.set_indicator()`** — ERPNext's native coloured dot system |
| Custom action buttons built in HTML | **`frm.add_custom_button()`** — ERPNext's standard button API |
| Custom dialogs in raw HTML | **`new frappe.ui.Dialog()`** — ERPNext's built-in modal system |
| Custom list row HTML | **`frappe.listview_settings`** — hooks into ERPNext's List View engine |
| Dark mode manually coded | **Automatic** — ERPNext handles light/dark via CSS variables |
| Custom number stat cards | **ERPNext Number Cards** — created as fixtures, shown in Workspace |
| Custom sidebar navigation | **ERPNext Workspace** — registered as a workspace JSON fixture |

## How ERPNext's UI actually works

When you install a proper Frappe app:

1. **DocType JSON** defines the fields, sections, and column breaks.
   ERPNext generates the form layout automatically — you never write form HTML.

2. **`doctype_js`** in hooks.py maps a JS controller to each DocType.
   This controller uses `frappe.ui.form.on()` to add behaviour — buttons,
   field events, validations — but never touches HTML directly.

3. **`doctype_list_js`** maps a list view controller via `frappe.listview_settings`.
   ERPNext renders the list; your code adds toolbar buttons, column formatters,
   and indicator colours.

4. **Workspace JSON** registers the module in ERPNext's sidebar with shortcuts,
   number cards, and report links — no sidebar HTML needed.

5. **Script Reports** return `(columns, data, message, chart, summary)`.
   ERPNext renders the report table, chart, and summary bar automatically.

## Files in this package

```
visitor_management/
├── hooks.py                          ← registers JS assets; zero CSS
├── public/js/
│   ├── visitor_entry.js              ← form controller (frappe.ui.form.on)
│   └── visitor_entry_list.js         ← list controller (frappe.listview_settings)
├── config/
│   └── visitor_management.json       ← Workspace definition (sidebar module)
├── fixtures/
│   └── number_cards.json             ← ERPNext Number Cards for dashboard
└── report/
    ├── daily_visitor_summary/        ← Script Report with chart + summary
    └── overstayed_visitors/          ← Script Report
```

The DocType JSON, Python controllers, workflow, print format, notifications,
and blacklist DocType remain unchanged from the first version — only the
client-side presentation layer has been replaced with native Frappe APIs.

## Installation (same as before)

```bash
bench get-app visitor_management /path/to/visitor_management
bench --site your-site.com install-app visitor_management
bench --site your-site.com migrate
bench build --app visitor_management
bench restart
```

After install, "Visitor Management" appears automatically in the ERPNext
sidebar as a first-class module — styled identically to HR, Accounts, etc.
