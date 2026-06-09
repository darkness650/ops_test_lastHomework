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
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


DEFAULT_PORT = 8080
DEFAULT_INVENTORY_SERVICE_URL = "http://inventoryservice"
DEFAULT_API_TOKEN = "online-boutique-restock"


class RestockHandler(BaseHTTPRequestHandler):
    inventory_service_url = DEFAULT_INVENTORY_SERVICE_URL
    api_token = DEFAULT_API_TOKEN
    request_counts = {"200": 0, "400": 0, "404": 0, "502": 0}
    request_counts_lock = Lock()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/_healthz":
            self.write_json(HTTPStatus.OK, {"status": "ok"})
            return

        if parsed.path == "/metrics":
            self.write_metrics()
            return

        self.write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        prefix = "/restock/"
        if not parsed.path.startswith(prefix):
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        if self.headers.get("Authorization") != f"Bearer {self.api_token}":
            self.write_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        product_id = unquote(parsed.path[len(prefix):]).strip("/")
        if not product_id:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": "product id is required"})
            return

        try:
            quantity = int(self.read_json().get("quantity", 0))
        except (TypeError, ValueError, json.JSONDecodeError):
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": "quantity must be an integer"})
            return

        if quantity <= 0:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": "quantity must be positive"})
            return

        try:
            inventory_response = self.restock_inventory(product_id, quantity)
        except HTTPError as err:
            body = err.read().decode("utf-8")
            self.write_json(
                HTTPStatus.BAD_GATEWAY,
                {
                    "error": "inventory service rejected restock",
                    "status": err.code,
                    "details": body,
                },
            )
            return
        except OSError as err:
            self.write_json(
                HTTPStatus.BAD_GATEWAY,
                {"error": "inventory service unavailable", "details": str(err)},
            )
            return

        self.write_json(
            HTTPStatus.OK,
            {
                "productId": product_id,
                "restocked": quantity,
                "inventory": inventory_response,
            },
        )

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}

        return json.loads(self.rfile.read(content_length).decode("utf-8"))

    def restock_inventory(self, product_id, quantity):
        url = f"{self.inventory_service_url}/inventory/{product_id}/release"
        payload = json.dumps({"quantity": quantity}).encode("utf-8")
        request = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))

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
            "# HELP restock_requests_total Restock HTTP responses by status code.",
            "# TYPE restock_requests_total counter",
        ]
        with self.request_counts_lock:
            for status, count in sorted(self.request_counts.items()):
                lines.append(f'restock_requests_total{{status="{status}"}} {count}')

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
    RestockHandler.inventory_service_url = os.environ.get(
        "INVENTORY_SERVICE_URL",
        DEFAULT_INVENTORY_SERVICE_URL,
    ).rstrip("/")
    RestockHandler.api_token = os.environ.get(
        "RESTOCK_API_TOKEN",
        DEFAULT_API_TOKEN,
    )

    server = ThreadingHTTPServer(("", port), RestockHandler)
    print(f"restockservice listening on port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
