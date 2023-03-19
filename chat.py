import asyncio
import json
import logging

import openai


openai.api_key_path = "static/key.txt"

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] [%(lineno)d %(funcName)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.FileHandler(f'logs/openai.log')],
    level=logging.INFO
)
logger = logging.getLogger("openai-chat")


class OpenaiResponseHandler:
    def __init__(self) -> None:
        """{
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
        }"""
        pass

    def handle(self, response) -> str:
        err_mess = None
        if not isinstance(response, dict):
            err_mess = f"Response format is not as expected: response should be a dictionary: {response}"
        elif response.get("choices") is None:
            err_mess = f"Response format is not as expected: \"choices\" did not present in response: {response}"
        elif not isinstance(response.get("choices"), list):
            err_mess = f"Response format is not as expected: \"choices\" is not a list: {response}"
        elif len(response.get("choices")) == 0:
            err_mess = f"Response format is not as expected: \"choices\" is empty: {response}"
        elif response.get("choices")[0].get("message") is None:
            err_mess = f"Response format is not as expected: \"choices[0].message\" is not presented: {response}"
        elif response.get("choices")[0].get("message").get("content") is None:
            err_mess = f"Response format is not as expected: \"choices[0].message.content\" is not presented: {response}"
        elif not isinstance(response.get("choices")[0].get("message").get("content"), str):
            err_mess = f"Response format is not as expected: \"choices[0].message.content\" is not a string: {response}"
        if err_mess:
            logger.error(err_mess)
            return "Opss, something wrong with openai. Please contact hy."

        return response.get("choices")[0].get("message").get("content")



async def req(body, mode="test"):
    logger.info(f"  >> >> >> >> >> >>  {body}")

    if mode == "test":
        await asyncio.sleep(1)
        with open('static/response_template.json', 'r') as f:
            res = json.load(f)
    elif mode == "openai":
        res = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=body
        )
    else:
        raise Exception(f"mode is either 'test' or 'openai', but not '{mode}'")
    logger.info(f"  << << << << << <<  {res}")
    return res
    


class SessionStorageSingleton(object):
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.lock = asyncio.Lock()
        return cls._instance

    def __init__(self) -> None:
        """data structure should be like this:
        {
            "mock_session_id_123": [
                {
                    "role": "system", 
                    "content": "You are a helpful assistant."
                }
            ]
        }
        """
        self._storage = {}
        self.known_roles = ("user", "system", "assistant")
    
    def construct_message(self, role:str, content:str):
        assert role in self.known_roles, f"Unknown role: {role}"
        return {
            "role": role, 
            "content": content
        }
    
    async def check_session_exist(self, sess_id: str) -> bool:
        async with self.lock:
            return sess_id in {k: v for k, v in self._storage.items() if v is not None}

    def get_messages(self, sess_id):
        return self._storage[sess_id]

    async def add_message_for(self, role: str, content: str, sess_id: str):
        async with self.lock:
            assert sess_id in self._storage.keys(), f"sess id: {sess_id} does not exist in storage: {self._storage.keys()}"
            self._storage[sess_id].append(
                self.construct_message(role, content)
            )

    async def new_session(self, sess_id):
        async with self.lock:
            """create a new session"""
            self._storage[sess_id] = [
                {"role": "system", "content": "You are a helpful assistant."}
            ]
            return sess_id

    async def del_session(self, sess_id:str):
        """delet a session
        """
        async with self.lock:
            del self._storage[sess_id]

    async def reset_session(self):
        """
        """
        async with self.lock:
            self._storage = {}


async def send_message(message: str, session_id: str, storage: SessionStorageSingleton, mode="test") -> str:

    # singleton
    sss = storage

    logger.info(f"storage: {sss._storage}")
    if not await sss.check_session_exist(sess_id=session_id):
        await sss.new_session(session_id)
    await sss.add_message_for(role="user", content=message, sess_id=session_id)

    res = await req(
        body=sss.get_messages(session_id),
        mode=mode
    )
    rh = OpenaiResponseHandler()
    ans = rh.handle(res)
    await sss.add_message_for(role="assistant", content=ans, sess_id=session_id)
    return ans



if __name__ == "__main__":
    asyncio.run(req)