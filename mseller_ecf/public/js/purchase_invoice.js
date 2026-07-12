frappe.ui.form.on("Purchase Invoice", {
  supplier(frm) {
    set_supplier_ecf_defaults(frm);
  },

  refresh(frm) {
    if (frm.doc.docstatus === 0) {
      set_supplier_ecf_defaults(frm);
    }

    if (frm.doc.docstatus !== 1 || !frm.doc.mseller_ecf_type || !frm.doc.mseller_ecf_ncf) {
      return;
    }

    frm.add_custom_button(__("Send e-CF"), () => {
      frappe.call({
        method: "mseller_ecf.mseller_ecf.api.public.enqueue_purchase_invoice",
        args: { invoice_name: frm.doc.name },
        freeze: true,
        callback() {
          frm.reload_doc();
        },
      });
    }, __("MSeller ECF"));

    frm.add_custom_button(__("View e-CF Log"), () => {
      frappe.set_route("List", "MSeller ECF Document", {
        purchase_invoice: frm.doc.name,
      });
    }, __("MSeller ECF"));

    frm.add_custom_button(__("Sync e-CF Status"), () => {
      frappe.call({
        method: "mseller_ecf.mseller_ecf.api.public.sync_purchase_invoice_status",
        args: { invoice_name: frm.doc.name },
        freeze: true,
        callback() {
          frm.reload_doc();
        },
      });
    }, __("MSeller ECF"));
  },
});

function set_supplier_ecf_defaults(frm) {
  if (!frm.doc.supplier || frm.doc.mseller_ecf_type) {
    return;
  }

  frappe.db
    .get_value("Supplier", frm.doc.supplier, ["mseller_ecf_default_type", "mseller_ecf_default_sequence"])
    .then((response) => {
      const defaults = response && response.message;
      if (!defaults) {
        return;
      }

      if (!frm.doc.mseller_ecf_type && defaults.mseller_ecf_default_type) {
        frm.set_value("mseller_ecf_type", defaults.mseller_ecf_default_type);
        return;
      }

      if (!frm.doc.mseller_ecf_type && defaults.mseller_ecf_default_sequence) {
        frappe.db
          .get_value("MSeller ECF Sequence", defaults.mseller_ecf_default_sequence, "ecf_type")
          .then((sequenceResponse) => {
            const sequence = sequenceResponse && sequenceResponse.message;
            if (sequence && sequence.ecf_type && !frm.doc.mseller_ecf_type) {
              frm.set_value("mseller_ecf_type", sequence.ecf_type);
            }
          });
      }
    });
}
