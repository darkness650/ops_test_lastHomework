#!/usr/bin/env python3
#
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import unquote, urlparse


DEFAULT_PORT = 8080


def load_inventory(path):
    with open(path, encoding="utf-8") as inventory_file:
        payload = json.load(inventory_file)

    products = payload.get("products", {})
    if not isinstance(products, dict):
        raise ValueError("inventory JSON must contain a products object")

    return products


class InventoryHandler(BaseHTTPRequestHandler):
    inventory = {}
    request_counts = {"200": 0, "404": 0}
    request_counts_lock = Lock()
    inventory_lock = Lock()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/_healthz":
            self.write_json(HTTPStatus.OK, {"status": "ok"})
            return

        if parsed.path == "/metrics":
            self.write_metrics()
            return

        prefix = "/inventory/"
        if not parsed.path.startswith(prefix):
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        product_id = unquote(parsed.path[len(prefix):]).strip("/")
        product_inventory = self.inventory.get(product_id)
        if product_inventory is None:
            self.write_json(
                HTTPStatus.NOT_FOUND,
                {"error": f"inventory for product {product_id} was not found"},
            )
            return

        self.write_json(HTTPStatus.OK, {"productId": product_id, **product_inventory})

    def do_POST(self):
        parsed = urlparse(self.path)
        action = None
        if parsed.path.startswith("/inventory/") and parsed.path.endswith("/reserve"):
            action = "reserve"
            product_id = parsed.path[len("/inventory/"):-len("/reserve")].strip("/")
        elif parsed.path.startswith("/inventory/") and parsed.path.endswith("/release"):
            action = "release"
            product_id = parsed.path[len("/inventory/"):-len("/release")].strip("/")
        else:
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        product_id = unquote(product_id)
        try:
            quantity = int(self.read_json().get("quantity", 0))
        except (TypeError, ValueError, json.JSONDecodeError):
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": "quantity must be an integer"})
            return

        if quantity <= 0:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": "quantity must be positive"})
            return

        if action == "reserve":
            self.reserve_inventory(product_id, quantity)
            return

        self.release_inventory(product_id, quantity)

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}

        return json.loads(self.rfile.read(content_length).decode("utf-8"))

    def reserve_inventory(self, product_id, quantity):
        with self.inventory_lock:
            product_inventory = self.inventory.get(product_id)
            if product_inventory is None:
                self.write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": f"inventory for product {product_id} was not found"},
                )
                return

            available = int(product_inventory["quantity"])
            if available < quantity:
                self.write_json(
                    HTTPStatus.CONFLICT,
                    {
                        "error": "insufficient inventory",
                        "productId": product_id,
                        "available": available,
                    },
                )
                return

            remaining = available - quantity
            product_inventory["quantity"] = remaining
            product_inventory["status"] = status_for_quantity(remaining)
            self.write_json(HTTPStatus.OK, {"productId": product_id, **product_inventory})

    def release_inventory(self, product_id, quantity):
        with self.inventory_lock:
            product_inventory = self.inventory.get(product_id)
            if product_inventory is None:
                self.write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": f"inventory for product {product_id} was not found"},
                )
                return

            product_inventory["quantity"] = int(product_inventory["quantity"]) + quantity
            product_inventory["status"] = status_for_quantity(product_inventory["quantity"])
            self.write_json(HTTPStatus.OK, {"productId": product_id, **product_inventory})

    def write_json(self, status, payload):
        with self.request_counts_lock:
            status_key = str(int(status))
            self.request_counts[status_key] = self.request_counts.get(status_key, 0) + 1

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_metrics(self):
        lines = [
            "# HELP inventory_requests_total Inventory HTTP responses by status code.",
            "# TYPE inventory_requests_total counter",
        ]
        with self.request_counts_lock:
            for status, count in sorted(self.request_counts.items()):
                lines.append(
                    f'inventory_requests_total{{status="{status}"}} {count}'
                )

        lines.extend(
            [
                "# HELP inventory_product_quantity Current stock quantity by product.",
                "# TYPE inventory_product_quantity gauge",
            ]
        )
        for product_id, item in sorted(self.inventory.items()):
            lines.append(
                'inventory_product_quantity{product_id="%s",status="%s"} %d'
                % (product_id, item["status"], item["quantity"])
            )

        body = ("\n".join(lines) + "\n").encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


def main():
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    inventory_path = Path(os.environ.get("INVENTORY_FILE", "inventory.json"))
    InventoryHandler.inventory = load_inventory(inventory_path)

    server = ThreadingHTTPServer(("", port), InventoryHandler)
    print(f"inventoryservice listening on port {port}", flush=True)
    server.serve_forever()


def status_for_quantity(quantity):
    if quantity <= 0:
        return "out_of_stock"
    if quantity <= 10:
        return "low_stock"
    return "in_stock"


if __name__ == "__main__":
    main()
