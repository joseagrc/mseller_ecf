# Operations

## Go-live checklist

- Configure **MSeller ECF Settings** in `TesteCF`.
- Send test invoices and confirm `MSeller ECF Document.status`.
- Correct item UOM mappings and tax indicators until DGII accepts the documents.
- Move to `CerteCF` for certification.
- Switch to `eCF` only after MSeller/DGII certification approval.
- Confirm print formats show e-NCF, security code, QR URL, issue date, and signed date.

## Statuses

- `Queued`: ERPNext submitted the invoice and queued the background job.
- `Pending`: payload was built and stored but not yet accepted by MSeller.
- `Sent`: MSeller accepted the payload for processing.
- `Aceptado`: DGII accepted the e-CF.
- `Aceptado Condicional`: DGII accepted with observations.
- `Rechazado`: DGII/MSeller rejected the document.
- `Error`: local integration or API request failed.

## Recovery

For transient failures:

```bash
bench --site your-site execute mseller_ecf.mseller_ecf.jobs.status_sync.sync_pending_documents
```

For a single document, use the **Sync Status** button on **MSeller ECF Document**.

If a submitted invoice never reached MSeller and remains `Error`, inspect `last_error`, fix configuration or fiscal data, then enqueue it again from:

```python
mseller_ecf.mseller_ecf.api.public.enqueue_sales_invoice
```
