# MSeller ECF

Frappe/ERPNext app for integrating Sales Invoices with MSeller e-CF.

The app sends ERPNext `Sales Invoice` documents to MSeller ECF, stores the immediate signing response, and synchronizes the final DGII status asynchronously.

## Features

- MSeller environment support: `TesteCF`, `CerteCF`, and `eCF`
- Secure settings DocType for credentials and API key
- Automatic custom fields on `Sales Invoice`
- Submit hook to enqueue e-CF sending
- Background status synchronization
- Individual and batch document status lookup
- Request/response audit DocType
- Conservative retry and token refresh handling

## Installation

From a Frappe bench:

```bash
bench get-app /path/to/mseller_ecf
bench --site your-site.localhost install-app mseller_ecf
bench --site your-site.localhost migrate
```

For Docker production images, add this app repository to `apps.json` and rebuild the custom Frappe image.

## Configuration

Open **MSeller ECF Settings** and configure:

- Enabled
- Environment
- Company
- MSeller email/password
- MSeller API key
- RNC and fiscal defaults
- Auto-send behavior

Use `TesteCF` first, then `CerteCF`, and only switch to `eCF` after certification.

## Operational Notes

- Do not cancel accepted e-CF invoices directly. Issue the corresponding electronic credit note when required.
- Validate item tax templates and company/customer tax IDs before enabling automatic sending.
- Review rejected documents in **MSeller ECF Document**; DGII error payloads are persisted for audit.
