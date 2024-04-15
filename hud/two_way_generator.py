import asyncio


class AsyncBuffer:

    def __init__(self):
        self.buffer = asyncio.Queue()

    async def append(self, value):
        await self.buffer.put(value)

    async def generator(self):
        while True:
            value = await self.buffer.get()
            self.buffer.task_done()
            yield value
