import json
import unittest
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

from inventory_service import InventoryHandler, load_inventory


class InventoryLoaderTest(unittest.TestCase):
    def test_load_inventory(self):
        inventory_path = Path(__file__).with_name("inventory.json")
        inventory = load_inventory(inventory_path)

        self.assertIn("OLJCESPC7Z", inventory)
        self.assertEqual(inventory["L9ECAV7KIM"]["status"], "out_of_stock")


class InventoryHandlerTest(unittest.TestCase):
    def test_unknown_route_returns_not_found(self):
        handler = InventoryHandler.__new__(InventoryHandler)
        handler.path = "/missing"
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        handler.do_GET()

        handler.send_response.assert_called_once_with(HTTPStatus.NOT_FOUND)

    def test_known_product_returns_inventory(self):
        handler = InventoryHandler.__new__(InventoryHandler)
        handler.inventory = {"ABC": {"quantity": 2, "status": "low_stock"}}
        handler.path = "/inventory/ABC"
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        handler.do_GET()

        handler.send_response.assert_called_once_with(HTTPStatus.OK)
        response = json.loads(handler.wfile.write.call_args.args[0].decode("utf-8"))
        self.assertEqual(response["productId"], "ABC")
        self.assertEqual(response["quantity"], 2)

    def test_metrics_expose_stock_quantity(self):
        handler = InventoryHandler.__new__(InventoryHandler)
        handler.inventory = {"ABC": {"quantity": 2, "status": "low_stock"}}
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        handler.write_metrics()

        body = handler.wfile.write.call_args.args[0].decode("utf-8")
        self.assertIn("inventory_requests_total", body)
        self.assertIn('product_id="ABC"', body)
        self.assertIn(" 2", body)

    def test_reserve_decrements_inventory(self):
        handler = make_handler(
            "/inventory/ABC/reserve",
            {"ABC": {"quantity": 3, "status": "low_stock"}},
            {"quantity": 2},
        )

        handler.do_POST()

        handler.send_response.assert_called_once_with(HTTPStatus.OK)
        self.assertEqual(handler.inventory["ABC"]["quantity"], 1)
        self.assertEqual(handler.inventory["ABC"]["status"], "low_stock")

    def test_reserve_rejects_insufficient_inventory(self):
        handler = make_handler(
            "/inventory/ABC/reserve",
            {"ABC": {"quantity": 1, "status": "low_stock"}},
            {"quantity": 2},
        )

        handler.do_POST()

        handler.send_response.assert_called_once_with(HTTPStatus.CONFLICT)
        self.assertEqual(handler.inventory["ABC"]["quantity"], 1)

    def test_release_restores_inventory(self):
        handler = make_handler(
            "/inventory/ABC/release",
            {"ABC": {"quantity": 0, "status": "out_of_stock"}},
            {"quantity": 2},
        )

        handler.do_POST()

        handler.send_response.assert_called_once_with(HTTPStatus.OK)
        self.assertEqual(handler.inventory["ABC"]["quantity"], 2)
        self.assertEqual(handler.inventory["ABC"]["status"], "low_stock")

def make_handler(path, inventory, payload):
    body = json.dumps(payload).encode("utf-8")
    handler = InventoryHandler.__new__(InventoryHandler)
    handler.inventory = inventory
    handler.path = path
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)
    handler.wfile = Mock()
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    return handler


if __name__ == "__main__":
    unittest.main()
