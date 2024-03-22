import asyncio
import json


class Client:
    async def send_ping(writer):
        print("Sending ping")
        writer.write(b"\x01")
        await writer.drain()

    async def send_data(writer, numbers):
        print("Sending data")
        writer.write(json.dumps(numbers).encode())
        await writer.drain()

    async def received(reader, chunck_size=100):
        data = await reader.read(chunck_size)
        print(f"Recieved data: {data}")
        return data
