frappe.ui.form.on("MSeller ECF Sequence", {
  refresh(frm) {
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
