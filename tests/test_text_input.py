import unittest
from unittest import mock

import server


class TextInputTests(unittest.TestCase):
    def setUp(self):
        self.client = server.socketio.test_client(server.app)
        self.addCleanup(self.client.disconnect)
        controller = mock.patch.object(server.keyboard_service, 'keyboard')
        self.keyboard = controller.start()
        self.addCleanup(controller.stop)

    def test_success_ack_preserves_chinese_english_emoji_spaces_and_newlines(self):
        text = '  中文选词 English 😀\n第二行\n\t '
        reply = self.client.emit('type_text', {'text': text}, callback=True)
        self.keyboard.type.assert_called_once_with(text)
        self.assertEqual(reply, {'ok': True})

    def test_whitespace_only_text_is_not_trimmed(self):
        reply = self.client.emit('type_text', {'text': ' \n\t '}, callback=True)
        self.keyboard.type.assert_called_once_with(' \n\t ')
        self.assertEqual(reply, {'ok': True})

    def test_invalid_payloads_do_not_call_system_input(self):
        for payload in (None, '', [], {}, {'text': ''}, {'text': None}, {'text': 1}, {'text': ['a']}):
            with self.subTest(payload=payload):
                reply = self.client.emit('type_text', payload, callback=True)
                self.assertFalse(reply['ok'])
                self.assertTrue(reply['message'])
        self.keyboard.type.assert_not_called()

    def test_input_failure_returns_ack_without_logging_draft(self):
        self.keyboard.type.side_effect = RuntimeError('private draft')
        with self.assertLogs('server', level='ERROR') as logs:
            reply = self.client.emit('type_text', {'text': 'private draft'}, callback=True)
        self.assertFalse(reply['ok'])
        self.assertIn('部分文字', reply['message'])
        self.assertNotIn('private draft', '\n'.join(logs.output))

    def test_legacy_client_can_send_without_requesting_ack(self):
        self.client.emit('type_text', {'text': '旧版客户端'})
        self.keyboard.type.assert_called_once_with('旧版客户端')

    def test_mode_switch_release_cancels_a_delayed_repeat_worker(self):
        with mock.patch('keyboard_service.threading.Thread') as worker, mock.patch(
            'keyboard_service.get_special_keys', return_value={},
        ):
            self.client.emit('key_action', {'key': 'a', 'action': 'down'})
            self.client.emit('key_action', {'key': 'a', 'action': 'up'})
            arguments = worker.call_args.kwargs['args']
            worker.call_args.kwargs['target'](*arguments)
        self.keyboard.press.assert_not_called()
        self.keyboard.release.assert_called_once_with('a')
        self.assertNotIn('a', server.keyboard_service.active_repeats)


if __name__ == '__main__':
    unittest.main()
