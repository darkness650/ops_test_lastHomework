import json
import unittest
from http import HTTPStatus
from io import BytesIO
from unittest.mock import Mock, patch

from restock_service import RestockHandler


class RestockHandlerTest(unittest.TestCase):
    def test_restock_calls_inventory_service(self):
        handler = make_handler("/restock/ABC", {"quantity": 5})
        handler.restock_inventory = Mock(return_value={"productId": "ABC", "quantity": 8})

        handler.do_POST()

        handler.restock_inventory.assert_called_once_with("ABC", 5)
        handler.send_response.assert_called_once_with(HTTPStatus.OK)
        response = json.loads(handler.wfile.write.call_args.args[0].decode("utf-8"))
        self.assertEqual(response["restocked"], 5)
        self.assertEqual(response["inventory"]["quantity"], 8)

    def test_restock_rejects_non_positive_quantity(self):
        handler = make_handler("/restock/ABC", {"quantity": 0})

        handler.do_POST()

        handler.send_response.assert_called_once_with(HTTPStatus.BAD_REQUEST)

    def test_metrics_expose_request_counter(self):
        handler = RestockHandler.__new__(RestockHandler)
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        handler.write_metrics()

        body = handler.wfile.write.call_args.args[0].decode("utf-8")
        self.assertIn("restock_requests_total", body)

    @patch("restock_service.urlopen")
    def test_restock_inventory_posts_release_request(self, urlopen_mock):
        response = Mock()
        response.read.return_value = json.dumps({"quantity": 6}).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen_mock.return_value = response

        handler = RestockHandler.__new__(RestockHandler)
        handler.inventory_service_url = "http://inventory"

        result = handler.restock_inventory("ABC", 2)

        self.assertEqual(result["quantity"], 6)
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "http://inventory/inventory/ABC/release")


def make_handler(path, payload):
    body = json.dumps(payload).encode("utf-8")
    handler = RestockHandler.__new__(RestockHandler)
    handler.path = path
    handler.headers = {
        "Authorization": "Bearer online-boutique-restock",
        "Content-Length": str(len(body)),
    }
    handler.rfile = BytesIO(body)
    handler.wfile = Mock()
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    return handler


if __name__ == "__main__":
    unittest.main()
