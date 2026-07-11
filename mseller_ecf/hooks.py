app_name = "mseller_ecf"
app_title = "MSeller ECF"
app_publisher = "MSeller ECF Integration"
app_description = "ERPNext integration with MSeller electronic invoicing"
app_email = "support@example.com"
app_license = "MIT"
required_apps = ["erpnext"]

doc_events = {
    "Sales Invoice": {
        "on_submit": "mseller_ecf.mseller_ecf.events.sales_invoice.on_submit",
        "on_cancel": "mseller_ecf.mseller_ecf.events.sales_invoice.on_cancel",
    }
}

scheduler_events = {
    "cron": {
        "*/15 * * * *": [
            "mseller_ecf.mseller_ecf.jobs.status_sync.sync_pending_documents",
        ],
    },
    "daily": [
        "mseller_ecf.mseller_ecf.jobs.status_sync.cleanup_expired_tokens",
    ],
}

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["name", "like", "Sales Invoice-mseller_ecf_%"]],
    },
    {
        "dt": "Property Setter",
        "filters": [["name", "like", "Sales Invoice-%mseller_ecf%"]],
    },
]

after_install = "mseller_ecf.mseller_ecf.install.after_install"

doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
}
