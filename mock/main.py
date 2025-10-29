import asyncio
import logging

from ElectricitySensor import ElectricitySensor
from MockPlug import MockPlug
from MockPlugUDPService import MockPlugUDPService
from mock.WaterSensor import WaterSensor

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point - demonstrates creating a mock plug with multiple sensors"""

    # Create a collection of mock sensors
    sensors = [
        ElectricitySensor("mock0sensor1", role='solar', update_interval=30.0),
        ElectricitySensor("mock0sensor2", role='appliance', update_interval=30.0),
        WaterSensor("mock0sensor3"),
    ]

    # Create plug with sensors
    mac = "mock0plug123"
    gateway_id = f"Powersensor-plug-{mac}-civet"
    plug = MockPlugUDPService(
        mac=mac,
        gateway_id=gateway_id,
        port=49476,
        sensors=sensors,
        protocol_class=MockPlug,
        properties={
            "version": "1",
            "id": mac,
        }
    )

    await plug.start()

    logger.info("=" * 60)
    logger.info("Mock Plug is running!")
    logger.info(f"Gateway ID: {plug.gateway_id}")
    logger.info(f"Sensors: {len(sensors)}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()  # Wait forever
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await plug.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service terminated")
