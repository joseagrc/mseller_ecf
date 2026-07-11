import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    create_sales_invoice_custom_fields()


def create_sales_invoice_custom_fields():
    fields = {
        "Sales Invoice": [
            {
                "fieldname": "mseller_ecf_section",
                "label": "MSeller ECF",
                "fieldtype": "Section Break",
                "insert_after": "tax_id",
                "collapsible": 1,
            },
            {
                "fieldname": "mseller_ecf_type",
                "label": "e-CF Type",
                "fieldtype": "Select",
                "insert_after": "mseller_ecf_section",
                "options": "\n31\n32\n33\n34\n41\n43\n44\n45\n46\n47",
            },
            {
                "fieldname": "mseller_ecf_ncf",
                "label": "e-NCF",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_type",
                "unique": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_status",
                "label": "e-CF Status",
                "fieldtype": "Select",
                "insert_after": "mseller_ecf_ncf",
                "options": "\nPending\nQueued\nSent\nAceptado\nAceptado Condicional\nRechazado\nError\nCancelled",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_col_break",
                "fieldtype": "Column Break",
                "insert_after": "mseller_ecf_status",
            },
            {
                "fieldname": "mseller_ecf_environment",
                "label": "MSeller Environment",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_col_break",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_internal_track_id",
                "label": "Internal Track ID",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_environment",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_security_code",
                "label": "Security Code",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_internal_track_id",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_signed_date",
                "label": "Signed Date",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_security_code",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_qr_url",
                "label": "QR URL",
                "fieldtype": "Small Text",
                "insert_after": "mseller_ecf_signed_date",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_last_sync",
                "label": "Last e-CF Sync",
                "fieldtype": "Datetime",
                "insert_after": "mseller_ecf_qr_url",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_last_error",
                "label": "Last e-CF Error",
                "fieldtype": "Small Text",
                "insert_after": "mseller_ecf_last_sync",
                "read_only": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_include_pagination",
                "label": "Include DGII Pagination",
                "fieldtype": "Check",
                "insert_after": "mseller_ecf_last_error",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_advanced_section",
                "label": "MSeller Advanced Fiscal Values",
                "fieldtype": "Section Break",
                "insert_after": "mseller_ecf_include_pagination",
                "collapsible": 1,
                "collapsible_depends_on": "eval:doc.mseller_ecf_type",
            },
            {
                "fieldname": "mseller_ecf_income_type",
                "label": "Income Type",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_advanced_section",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_payment_type",
                "label": "Payment Type",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_income_type",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_sequence_expiry_date",
                "label": "Sequence Expiry Date",
                "fieldtype": "Date",
                "insert_after": "mseller_ecf_payment_type",
                "allow_on_submit": 1,
            },
        ],
        "Sales Invoice Item": [
            {
                "fieldname": "mseller_ecf_billing_indicator",
                "label": "e-CF Billing Indicator",
                "fieldtype": "Data",
                "insert_after": "item_tax_template",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "mseller_ecf_goods_service_indicator",
                "label": "e-CF Goods/Service Indicator",
                "fieldtype": "Data",
                "insert_after": "mseller_ecf_billing_indicator",
                "allow_on_submit": 1,
            },
        ],
    }

    create_custom_fields(fields, update=True)
    frappe.db.commit()
