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

    def test_clear_ack_and_platform_key_order(self):
        key = server.keyboard_service.Key
        for system, modifier in [('Darwin', key.cmd), ('Windows', key.ctrl), ('Linux', key.ctrl)]:
            with self.subTest(system=system), mock.patch('keyboard_service.platform.system', return_value=system), mock.patch('keyboard_service.time.sleep'):
                self.keyboard.reset_mock()
                reply = self.client.emit('clear_text', {}, callback=True)
                self.assertEqual(reply, {'ok': True})
                self.assertEqual(self.keyboard.mock_calls, [
                    mock.call.press(modifier), mock.call.press('a'),
                    mock.call.release('a'), mock.call.release(modifier),
                    mock.call.press(key.backspace), mock.call.release(key.backspace),
                ])

    def test_clear_failure_releases_keys_and_returns_failure_ack(self):
        key = server.keyboard_service.Key
        for failure_at in range(6):
            with self.subTest(failure_at=failure_at), mock.patch('keyboard_service.platform.system', return_value='Darwin'), mock.patch('keyboard_service.time.sleep'):
                self.keyboard.reset_mock()
                events = []
                def action(kind, target):
                    events.append((kind, target))
                    if len(events) == failure_at + 1:
                        raise RuntimeError('private error')
                self.keyboard.press.side_effect = lambda target: action('press', target)
                self.keyboard.release.side_effect = lambda target: action('release', target)
                with self.assertLogs('server', level='ERROR') as logs:
                    reply = self.client.emit('clear_text', {}, callback=True)
                self.assertFalse(reply['ok'])
                self.assertTrue(reply['message'])
                self.assertNotIn('private error', '\n'.join(logs.output))
                for index, (kind, target) in enumerate(events):
                    if kind == 'press':
                        self.assertIn(('release', target), events[index + 1:])
                if failure_at < 4:
                    self.assertNotIn(('press', key.backspace), events)

    def test_clear_cleanup_continues_if_one_release_fails(self):
        key = server.keyboard_service.Key
        self.keyboard.press.side_effect = [None, RuntimeError('press failed')]
        self.keyboard.release.side_effect = [RuntimeError('release failed'), None]
        with mock.patch('keyboard_service.platform.system', return_value='Darwin'), mock.patch('keyboard_service.time.sleep'), self.assertLogs('server', level='ERROR'):
            reply = self.client.emit('clear_text', {}, callback=True)
        self.assertFalse(reply['ok'])
        self.assertEqual(self.keyboard.release.call_args_list, [mock.call('a'), mock.call(key.cmd)])


if __name__ == '__main__':
    unittest.main()
