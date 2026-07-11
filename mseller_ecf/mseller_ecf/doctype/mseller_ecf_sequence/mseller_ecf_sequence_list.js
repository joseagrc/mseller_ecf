frappe.listview_settings["MSeller ECF Sequence"] = {
  get_indicator(doc) {
    if (doc.status === "Active") {
      return [__("Active"), "green", "status,=,Active"];
    }
    if (doc.status === "Exhausted") {
      return [__("Exhausted"), "red", "status,=,Exhausted"];
    }
    if (doc.status === "Expired") {
      return [__("Expired"), "orange", "status,=,Expired"];
    }
    return [__(doc.status), "gray", `status,=,${doc.status}`];
  },
};
