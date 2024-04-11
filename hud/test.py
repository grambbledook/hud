import asyncio
from bleak import BleakScanner, BleakClient

HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

async def main():
    scanner = BleakScanner()
    devices = await scanner.discover()

    heart_rate_monitor = None
    for device in devices:
        if HEART_RATE_SERVICE_UUID in device.metadata["uuids"]:
            heart_rate_monitor = device
            break

    if heart_rate_monitor is None:
        print("Heart rate monitor not found.")
        return

    # Connect to the heart rate monitor
    client = BleakClient(heart_rate_monitor)
    await client.connect()

    def on_data(sender: int, data: bytearray):
        print(f"Heart rate: {data[1]}")

    await client.start_notify(HEART_RATE_MEASUREMENT_CHAR_UUID, on_data)

    await asyncio.sleep(10)

    await client.stop_notify(HEART_RATE_MEASUREMENT_CHAR_UUID)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())