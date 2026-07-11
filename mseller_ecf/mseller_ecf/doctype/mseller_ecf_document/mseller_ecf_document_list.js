frappe.listview_settings["MSeller ECF Document"] = {
  add_fields: ["status", "sales_invoice", "ecf", "environment"],
  get_indicator(doc) {
    const colorMap = {
      Aceptado: "green",
      "Aceptado Condicional": "orange",
      Rechazado: "red",
      Error: "red",
      Sent: "blue",
      Queued: "yellow",
      Pending: "yellow",
      Cancelled: "gray",
    };
    return [__(doc.status || "Pending"), colorMap[doc.status] || "gray", `status,=,${doc.status}`];
  },
};
