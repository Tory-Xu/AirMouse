import base64
import io
import socket
import unittest
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest import mock

from PIL import Image

from web_app import app, get_all_ip_addresses, get_default_ip_address, make_qr_data_uri


class PageElements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.by_id = {}
        self.options = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.by_id[attrs['id']] = attrs
        if tag == 'option':
            self.options.append(attrs)


class NetworkAddressTests(unittest.TestCase):
    def test_only_active_usable_ipv4_addresses_are_listed(self):
        def address(value, family=socket.AF_INET):
            return SimpleNamespace(family=family, address=value)

        interfaces = {
            'Wi-Fi': [address(value) for value in (
                '192.168.1.20', '192.168.1.20', '127.0.0.1', '169.254.10.1',
                '0.0.0.0', '255.255.255.255', '224.0.0.1', '240.0.0.1', 'invalid',
            )] + [address('fe80::1', socket.AF_INET6)],
            'Ethernet': [address('10.0.0.8')],
            'Disabled': [address('192.168.5.1')],
            'Unknown': [address('192.168.6.1')],
        }
        stats = {name: SimpleNamespace(isup=name != 'Disabled') for name in interfaces if name != 'Unknown'}
        with mock.patch('web_app.psutil.net_if_addrs', return_value=interfaces), mock.patch(
            'web_app.psutil.net_if_stats', return_value=stats,
        ):
            self.assertEqual(get_all_ip_addresses(), [('Wi-Fi', '192.168.1.20'), ('Ethernet', '10.0.0.8')])

    def test_interface_detection_failure_returns_no_addresses(self):
        with mock.patch('web_app.psutil.net_if_addrs', side_effect=OSError), self.assertLogs(level='WARNING'):
            self.assertEqual(get_all_ip_addresses(), [])

    def test_outbound_address_uses_local_route_without_sending_packets(self):
        with mock.patch('web_app.socket.socket') as socket_factory:
            probe = socket_factory.return_value.__enter__.return_value
            probe.getsockname.return_value = ('192.168.1.20', 12345)
            self.assertEqual(get_default_ip_address(), '192.168.1.20')
            socket_factory.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect.assert_called_once_with(('192.0.2.1', 9))
            probe.send.assert_not_called()
            probe.sendto.assert_not_called()
            socket_factory.return_value.__exit__.assert_called_once()

    def test_no_default_route_is_allowed(self):
        with mock.patch('web_app.socket.socket', side_effect=OSError):
            self.assertIsNone(get_default_ip_address())

    def test_qr_is_a_local_png_with_a_white_quiet_zone(self):
        uri = make_qr_data_uri('https://192.168.1.20:5888/')
        self.assertTrue(uri.startswith('data:image/png;base64,'))
        data = base64.b64decode(uri.split(',', 1)[1], validate=True)
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.format, 'PNG')
            self.assertEqual(image.width, image.height)
            self.assertEqual(image.convert('RGB').crop((0, 0, image.width, 32)).getextrema(), ((255, 255),) * 3)


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        addresses = mock.patch('web_app.get_all_ip_addresses', return_value=[
            ('Ethernet', '10.0.0.8'), ('Wi-Fi', '192.168.1.20'),
        ])
        route = mock.patch('web_app.get_default_ip_address', return_value='192.168.1.20')
        self.addresses = addresses.start()
        self.route = route.start()
        self.addCleanup(addresses.stop)
        self.addCleanup(route.stop)

    def page(self, **kwargs):
        with self.client.get('/', **kwargs) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            return PageElements(response.get_data(as_text=True))

    def test_localhost_prefers_default_outbound_interface(self):
        page = self.page(base_url='https://localhost:5888')
        self.assertEqual(page.by_id['connection-url']['value'], 'https://192.168.1.20:5888/')
        self.assertEqual(len(page.options), 2)
        self.assertIn('selected', page.options[1])
        self.assertEqual(page.by_id['connection-qr']['src'], page.options[1]['data-qr'])

    def test_current_lan_host_takes_priority_over_default_route(self):
        page = self.page(base_url='https://10.0.0.8:5888')
        self.assertEqual(page.by_id['connection-url']['value'], 'https://10.0.0.8:5888/')
        self.assertIn('selected', page.options[0])
        self.route.assert_not_called()

    def test_all_interfaces_have_matching_https_urls_and_qr_codes(self):
        with mock.patch('web_app.make_qr_data_uri', wraps=make_qr_data_uri) as qr:
            page = self.page()
        self.assertEqual([option['value'] for option in page.options], [
            'https://10.0.0.8:5888/', 'https://192.168.1.20:5888/',
        ])
        self.assertEqual(qr.call_args_list, [mock.call(option['value']) for option in page.options])

    def test_invalid_host_and_unlisted_outbound_address_fall_back_to_detected_interface(self):
        self.route.return_value = '172.16.0.1'
        page = self.page(base_url='https://untrusted.example:9999')
        self.assertEqual(page.by_id['connection-url']['value'], 'https://10.0.0.8:5888/')

    def test_lan_without_default_route_still_has_qr(self):
        self.route.return_value = None
        page = self.page()
        self.assertEqual(page.by_id['connection-url']['value'], 'https://10.0.0.8:5888/')

    def test_no_network_shows_connection_hint_without_qr(self):
        self.addresses.return_value = []
        page = self.page()
        self.assertIn('connection-empty', page.by_id)
        self.assertNotIn('connection-qr', page.by_id)
        self.assertNotIn('connection-url', page.by_id)

    def test_refresh_redetects_changed_ip(self):
        self.page()
        self.addresses.return_value = [('Wi-Fi', '192.168.1.30')]
        page = self.page()
        self.assertEqual(self.addresses.call_count, 2)
        self.assertEqual(page.by_id['connection-url']['value'], 'https://192.168.1.30:5888/')
        self.assertIn('disabled', page.by_id['connection-interface'])

    def test_keyboard_defaults_to_text_editor_and_bundles_its_scripts(self):
        with self.client.get('/k') as response:
            self.assertEqual(response.status_code, 200)
            page = PageElements(response.get_data(as_text=True))
        self.assertIn('text-input', page.by_id)
        self.assertEqual(page.by_id['clear-text']['type'], 'button')
        self.assertEqual(page.by_id['clear-text']['aria-describedby'], 'clear-hint')
        self.assertEqual(page.by_id['text-mode-button']['aria-pressed'], 'true')
        self.assertIn('hidden', page.by_id['full-keyboard'])
        for script in ('connection.js', 'text-input.js', 'socket.io.min.js'):
            with self.subTest(script=script), self.client.get('/static/js/' + script) as response:
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data)

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
