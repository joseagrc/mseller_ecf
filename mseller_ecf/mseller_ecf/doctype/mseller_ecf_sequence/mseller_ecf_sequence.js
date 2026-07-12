frappe.ui.form.on("MSeller ECF Sequence", {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__("Refresh Status"), () => {
        frappe.call({
          method: "mseller_ecf.mseller_ecf.jobs.sequence_sync.refresh_sequence_status",
          args: {
            sequence_name: frm.doc.name,
          },
          freeze: true,
          freeze_message: __("Refreshing sequence status..."),
          callback() {
            frm.reload_doc();
          },
        });
      });
    }

    if (frm.doc.prefix && frm.doc.next_number && frm.doc.padding_length) {
      frm.dashboard.add_comment(
        __("Next e-NCF: {0}", [
          `${frm.doc.prefix}${String(frm.doc.next_number).padStart(frm.doc.padding_length, "0")}`,
        ]),
        "blue",
        true
      );
    }
  },
});
