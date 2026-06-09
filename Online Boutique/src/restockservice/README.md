# Restock Service

`restockservice` is an HTTP microservice added for the course project. It
accepts replenishment requests and updates product inventory by calling
`inventoryservice`.

## API

```http
POST /restock/{product_id}
Content-Type: application/json

{"quantity": 5}
```

Example response:

```json
{
  "productId": "66VCHSJNUP",
  "restocked": 5,
  "inventory": {
    "productId": "66VCHSJNUP",
    "quantity": 7,
    "status": "low_stock",
    "warehouse": "Shanghai-A"
  }
}
```

The service also exposes:

- `GET /_healthz` for Kubernetes probes.
- `GET /metrics` for Prometheus request counters.
