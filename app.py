from chat import SessionStorageSingleton, send_message
from wechaty import Wechaty, Message
import asyncio, os

os.environ["WECHATY_PUPPET_SERVICE_ENDPOINT"] = "127.0.0.1:8080"
os.environ["WECHATY_PUPPET_SERVICE_TOKEN"] ="9c577ae4-e040-46d5-82bb-0b34592c8360" # 之前uuid生成的token

os.environ["WECHATY_PUPPET_WECHAT_PUPPETEER_UOS"] = "true"

os.environ["MODE"] = "openai"  # test / openai


bot = Wechaty()

sss = SessionStorageSingleton()

class MyBot(Wechaty):
    async def on_message(self, msg: Message) -> None:
        talker = msg.talker()
        room = msg.room()
        text = msg.text()
        if room:
            sess = await room.topic()
        else:
            sess = talker.name

        if text.startswith("#?"):
            res = await send_message(
                message=text[2:], 
                session_id=sess, 
                storage=sss, 
                mode=os.getenv("MODE"))
            await msg.say(f"GPT: {res}")

        elif text.startswith("#!!"):
            await sss.reset_session()
            await msg.say(f"sess reseted")

        elif text.startswith("#!"):
            await sss.del_session(sess_id=sess)
            await msg.say(f"sess deleted: {sess}")

asyncio.run(MyBot().start())