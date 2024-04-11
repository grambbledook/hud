import asyncio
from bleak import BleakScanner

import bluetooth


async def main():
    print('Discovering bluetooth devices ...')
    devices = await BleakScanner.discover(return_adv=True)
    for i, d in enumerate(devices):
        print(f"{i}: {d}")

asyncio.run(main())
