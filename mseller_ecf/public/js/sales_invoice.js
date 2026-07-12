frappe.ui.form.on("Sales Invoice", {
  refresh(frm) {
    if (frm.doc.docstatus !== 1 || !frm.doc.mseller_ecf_type || !frm.doc.mseller_ecf_ncf) {
      return;
    }

    frm.add_custom_button(__("Send e-CF"), () => {
      frappe.call({
        method: "mseller_ecf.mseller_ecf.api.public.enqueue_sales_invoice",
        args: { invoice_name: frm.doc.name },
        freeze: true,
        callback() {
          frm.reload_doc();
        },
      });
    }, __("MSeller ECF"));

    frm.add_custom_button(__("View e-CF Log"), () => {
      frappe.set_route("List", "MSeller ECF Document", {
        sales_invoice: frm.doc.name,
      });
    }, __("MSeller ECF"));

    frm.add_custom_button(__("Sync e-CF Status"), () => {
      frappe.call({
        method: "mseller_ecf.mseller_ecf.api.public.sync_sales_invoice_status",
        args: { invoice_name: frm.doc.name },
        freeze: true,
        callback() {
          frm.reload_doc();
        },
      });
    }, __("MSeller ECF"));
  },
});
