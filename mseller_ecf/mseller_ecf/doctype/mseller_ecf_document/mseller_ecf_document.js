frappe.ui.form.on("MSeller ECF Document", {
  refresh(frm) {
    if (!frm.is_new() && frm.doc.ecf) {
      frm.add_custom_button(__("Sync Status"), () => {
        frappe.call({
          method: "mseller_ecf.mseller_ecf.jobs.status_sync.sync_document",
          args: { document_name: frm.doc.name },
          freeze: true,
          callback() {
            frm.reload_doc();
          },
        });
      });
    }
  },
});
