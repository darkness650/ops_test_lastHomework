# Inventory Service

`inventoryservice` is an HTTP microservice added for the course project. It
returns stock information for Online Boutique products so the frontend can show
availability on product detail pages.

## API

```http
GET /inventory/{product_id}
```

Example response:

```json
{
  "productId": "OLJCESPC7Z",
  "quantity": 18,
  "status": "in_stock",
  "warehouse": "Shanghai-A"
}
```

The service also exposes:

- `GET /_healthz` for Kubernetes probes.
- `GET /metrics` with Prometheus request and stock metrics.
