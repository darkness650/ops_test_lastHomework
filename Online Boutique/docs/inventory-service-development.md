# Inventory Service Development

This course-project extension adds `inventoryservice` and `restockservice` to
Online Boutique and integrates them with the existing Go frontend.

## Interaction

1. A user opens a product detail page.
2. The frontend retrieves product data from `productcatalogservice`.
3. The frontend sends `GET /inventory/{product_id}` to `inventoryservice`.
4. The page displays the stock status, quantity, and warehouse.
5. The add-to-cart action is disabled when the product is out of stock.
6. Operators open `/admin/restock`, sign in with an administrator account, and
   submit incoming stock from the independent inventory administration module.
   The frontend calls `restockservice`, which updates stock through
   `inventoryservice`.

The inventory call is non-critical. If the service is unavailable, the product
page still renders without inventory information. This behavior is useful for
Chaos Mesh experiments because the failure is visible in logs and metrics
without taking down the entire shopping flow.

## Monitoring

Prometheus can scrape `GET /metrics` from port `8080`. The Kubernetes pod
contains the standard `prometheus.io` annotations.

Available metrics:

- `inventory_requests_total{status="..."}`: HTTP response count.
- `inventory_product_quantity{product_id="...",status="..."}`: current stock.
- `restock_requests_total{status="..."}`: replenishment HTTP response count.

Useful Grafana queries:

```promql
rate(inventory_requests_total[1m])
```

```promql
inventory_product_quantity
```

## Local test

```powershell
cd src/inventoryservice
python -m unittest
python inventory_service.py
```

Then request:

```text
http://localhost:8080/inventory/OLJCESPC7Z
http://localhost:8080/metrics
```

## Admin Restock

Default local administrator credentials:

```text
username: admin
password: admin123
```

The credentials can be changed with these frontend environment variables:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_TOKEN`

The internal frontend-to-restock service call also uses `RESTOCK_API_TOKEN`.
