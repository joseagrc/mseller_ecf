app_name = "mseller_ecf"
app_title = "MSeller ECF"
app_publisher = "MSeller ECF Integration"
app_description = "ERPNext integration with MSeller electronic invoicing"
app_email = "support@example.com"
app_license = "MIT"
required_apps = ["erpnext"]

doc_events = {
    "Sales Invoice": {
        "before_submit": "mseller_ecf.mseller_ecf.events.sales_invoice.before_submit",
        "on_submit": "mseller_ecf.mseller_ecf.events.sales_invoice.on_submit",
        "on_cancel": "mseller_ecf.mseller_ecf.events.sales_invoice.on_cancel",
    }
}

scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "mseller_ecf.mseller_ecf.jobs.status_sync.sync_pending_documents",
        ],
    },
    "daily": [
        "mseller_ecf.mseller_ecf.jobs.status_sync.cleanup_expired_tokens",
    ],
    "hourly": [
        "mseller_ecf.mseller_ecf.jobs.sequence_sync.refresh_all_sequence_statuses",
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
after_migrate = "mseller_ecf.mseller_ecf.install.create_sales_invoice_custom_fields"

doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
}
