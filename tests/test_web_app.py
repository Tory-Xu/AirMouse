import unittest

from web_app import app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_dashboard_is_available(self):
        response = self.client.get('/')
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'AirMouse', response.data)
        finally:
            response.close()

    def test_packaged_static_resource_path_is_available(self):
        response = self.client.get('/static/touchpad.png')
        try:
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(response.data), 0)
        finally:
            response.close()


if __name__ == '__main__':
    unittest.main()
