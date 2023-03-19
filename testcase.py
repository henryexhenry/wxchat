import asyncio
import unittest
from unittest.mock import patch
from chat import OpenaiResponseHandler, SessionStorageSingleton, req, send_message


class TestSessionStorageSingleton(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.session_storage = SessionStorageSingleton()
        self.session_id = "mock_session_id_123"
        await self.session_storage.new_session(self.session_id)

    async def test_new_session(self):
        session_id = "new_mock_session_id"
        result = await self.session_storage.new_session(session_id)
        self.assertEqual(result, session_id)
        self.assertIn(session_id, self.session_storage._storage)

    async def test_check_session_exist(self):
        result = await self.session_storage.check_session_exist(self.session_id)
        self.assertTrue(result)

        result = await self.session_storage.check_session_exist("nonexistent_session_id")
        self.assertFalse(result)

    async def test_add_message_for(self):
        role = "user"
        content = "Hello, this is a test message."
        await self.session_storage.add_message_for(role, content, self.session_id)
        messages = self.session_storage.get_messages(self.session_id)
        self.assertEqual(len(messages), 2)
        self.assertIn({"role": role, "content": content}, messages)

    async def test_add_message_for_invalid_session(self):
        role = "user"
        content = "Hello, this is a test message."
        with self.assertRaises(AssertionError):
            await self.session_storage.add_message_for(role, content, "nonexistent_session_id")

    async def test_del_session(self):
        await self.session_storage.del_session(self.session_id)
        self.assertNotIn(self.session_id, self.session_storage._storage)



class TestOpenaiResponseHandler(unittest.TestCase):
    def setUp(self):
        self.handler = OpenaiResponseHandler()

    @patch("chat.logger.error")
    def test_handle(self, mock_error):
        # Test a valid response
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "content": "The 2020 World Series was played in Globe Life Field in Arlington, Texas.",
                        "role": "assistant"
                    }
                }
            ],
            "created": 1677928297,
            "id": "chatcmpl-6qK5Z2dHLAPyyID8lhbP2ElNAcONZ",
            "model": "gpt-3.5-turbo-0301",
            "object": "chat.completion",
            "usage": {
                "completion_tokens": 19,
                "prompt_tokens": 56,
                "total_tokens": 75
            }
        }

        expected_output = "The 2020 World Series was played in Globe Life Field in Arlington, Texas."
        self.assertEqual(self.handler.handle(response), expected_output)
        mock_error.assert_not_called()

        # Test an invalid response with missing "choices"
        response = {
            "created": 1677928297,
            "id": "chatcmpl-6qK5Z2dHLAPyyID8lhbP2ElNAcONZ",
            "model": "gpt-3.5-turbo-0301",
            "object": "chat.completion",
            "usage": {
                "completion_tokens": 19,
                "prompt_tokens": 56,
                "total_tokens": 75
            }
        }

        expected_output = "Opss, something wrong with openai. Please contact hy."
        self.assertEqual(self.handler.handle(response), expected_output)
        mock_error.assert_called_once_with('Response format is not as expected: "choices" did not present in response: {}'.format(response))



class TestSendMessage(unittest.IsolatedAsyncioTestCase):

    @patch('chat.SessionStorageSingleton')
    @patch('chat.OpenaiResponseHandler')
    @patch('chat.req')
    async def test_send_message(self, mock_req, mock_response_handler, mock_session_storage):
        # Setup
        session_id = 'test_session'
        user_message = 'Hello!'
        expected_openai_response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "content": "Hi there!",
                        "role": "assistant"
                    }
                }
            ],
            "created": 1677928297,
            "id": "chatcmpl-6qK5Z2dHLAPyyID8lhbP2ElNAcONZ",
            "model": "gpt-3.5-turbo-0301",
            "object": "chat.completion",
            "usage": {
                "completion_tokens": 19,
                "prompt_tokens": 56,
                "total_tokens": 75
            }
        }

        mock_session_storage.return_value.check_session_exist.return_value = False
        mock_req.return_value = expected_openai_response

        mock_response_handler.return_value.handle.return_value = 'Hi there!'

        # Exercise
        response = await send_message(user_message, session_id)

        # Assert
        mock_session_storage.return_value.check_session_exist.assert_called_once_with(sess_id=session_id)
        mock_session_storage.return_value.new_session.assert_called_once_with(session_id)
        mock_session_storage.return_value.add_message_for.assert_called_once_with(role='user', message=user_message, sess_id=session_id)
        mock_req.assert_called_once_with(body=mock_session_storage.return_value.get_messages.return_value)
        mock_response_handler.return_value.handle.assert_called_once_with(expected_openai_response)
        self.assertEqual(response, 'Hi there!')


class TestReq(unittest.TestCase):

    @patch('chat.json.load')
    @patch('chat.openai.ChatCompletion.acreate')
    def test_req(self, mock_openai, mock_json_load):
        res_temp = {
            "choices": [
                {
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": "The 2020 World Series was played in Globe Life Field in Arlington, Texas.",
                    "role": "assistant"
                }
                }
            ],
            "created": 1677928297,
            "id": "chatcmpl-6qK5Z2dHLAPyyID8lhbP2ElNAcONZ",
            "model": "gpt-3.5-turbo-0301",
            "object": "chat.completion",
            "usage": {
                "completion_tokens": 19,
                "prompt_tokens": 56,
                "total_tokens": 75
            }
        }
        mock_json_load.return_value = {"response": "test"}
        mock_openai.return_value = res_temp
        body = {"message": "test"}
        res = asyncio.run(req(body, "test"))

        mock_json_load.assert_called_once_with('static/response_template.json')
        mock_openai.assert_not_called()
        self.assertEqual(res, {"response": "test"})

        res = asyncio.run(req(body, "openai"))

        mock_json_load.assert_called_once_with('static/response_template.json')
        mock_openai.assert_called_once_with(model="gpt-3.5-turbo", messages=body)
        self.assertEqual(res, res_temp)

