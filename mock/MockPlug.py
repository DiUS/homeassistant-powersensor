import asyncio
import datetime
import json
import random
from typing import Optional, List

import numpy as np

from MockSensor import MockSensor
import logging
logger = logging.getLogger(__name__)


def random_sample_duration():
    if np.random.rand() < 0.5:
        return np.random.normal(0.96, 0.00025)
    else:
        return np.random.normal(1.04, 0.00025)

def random_sample_power():
    if np.random.rand() < 0.25:
        return np.random.normal(58.15, 0.26)
    else:
        return np.random.normal(59.8, 0.4)

def random_sample_reactive_current():
    if np.random.rand() < 0.25:
        return np.random.normal(.305, 0.0002)
    else:
        return np.random.normal(.318, 0.002)


class MockPlug(asyncio.DatagramProtocol):
    """
    Simulated Plug!
    Generates both plug messages and relayed sensor messages.
    """

    def __init__(self, mac: str, gateway_id: str, sensors: Optional[List[MockSensor]] = None):
        self.mac = mac
        self.gateway_id = gateway_id
        self.sensors = sensors or []
        self.transport = None
        self.sensor_tasks = []
        self.subscribers = set()  # Track subscribed clients
        self.broadcast_lock = asyncio.Lock()  # Prevent concurrent broadcasts

    def connection_made(self, transport):
        self.transport = transport
        sock = transport.get_extra_info('socket')
        logger.info(f"Mock Plug {self.gateway_id} UDP server started on {sock.getsockname()}")

        # Start all sensor tasks
        for sensor in self.sensors:
            task = asyncio.create_task(sensor.run(self._handle_sensor_reading))
            self.sensor_tasks.append(task)


        asyncio.create_task(self._send_plug_data())

    def datagram_received(self, data, addr):
        """Handle incoming UDP packets"""
        logger.info(f"Received {len(data)} bytes from {addr}")

        # Try to decode as plain text first (for subscribe commands)
        try:
            message_str = data.decode('utf-8').strip()

            # Handle subscribe command
            if message_str.startswith('subscribe('):
                self.handle_subscribe(message_str, addr)
                return

            # Try parsing as JSON
            try:
                # We need to handle this possibility...we could add better message handling if it matters...
                message = json.loads(message_str)
                logger.info(f"Parsed JSON message: {message}")
                logger.info(f"Gateway {self.gateway_id} received: {message}")
            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON text from {addr}: {message_str}")

        except UnicodeDecodeError:
            logger.warning(f"Could not decode message from {addr}: {data}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def handle_subscribe(self, message_str: str, addr: tuple):
        """
        Handle subscription requests from clients.
        Format: subscribe(num) where num is subscriber ID
        subscribe(0) = disconnect/unsubscribe
        """
        logger.info(f"Client {addr} sent: {message_str}")

        # Check if this is a disconnect (subscribe(0))
        if 'subscribe(0)' in message_str:
            if addr in self.subscribers:
                self.subscribers.discard(addr)
                logger.info(f"Client {addr} unsubscribed. Total subscribers: {len(self.subscribers)}")
            else:
                logger.warning(f"Client {addr} tried to unsubscribe but was not subscribed")
        else:
            # Add to subscribers list
            self.subscribers.add(addr)
            logger.info(f"Client {addr} subscribed. Total subscribers: {len(self.subscribers)}")


    async def _handle_sensor_reading(self, reading: dict):
        """
        Internal callback for when sensors generate readings.
        For now, it just replays it back, we could do more...
        """
        async with self.broadcast_lock:
            self.broadcast_message(reading)
            logger.debug(f"Relayed sensor reading: {reading['mac']}")

    async def _send_plug_data(self):
        """Send periodic plug status messages"""
        while True:
            duration = random_sample_duration()
            await asyncio.sleep(duration)
            t = datetime.datetime.now(datetime.timezone.utc).timestamp()
            v = np.random.normal(240, 1.2)
            p = random_sample_power()
            active_current = p / v - random.random() / 1000
            reactive_current = random_sample_reactive_current()
            current = np.sqrt(active_current ** 2 + reactive_current ** 2) + 0.016 + (random.random() - 0.5) / 1000
            message = {
                'reactive_current': reactive_current,
                'type': 'instant_power',
                'summation_start': 1760615946.173936,
                'count': random.randint(12, 13),
                'duration': duration,
                'role': 'appliance',
                'power': p,
                'unit': 'W',
                'device': 'plug',
                'source': 'BLE',
                'active_current': active_current,
                'mac': self.mac,
                'voltage': v,
                'starttime': t,
                'current': current,
                'borrowed_summation': 0,
                'summation': 59.5649065 * t - 1.04883909e+11
            }
            async with self.broadcast_lock:
                self.broadcast_message(message)
                logger.info(f"Plug {self.mac} sent data!")

    def send_message(self, message: dict, addr: tuple):
        """Send a message to a specific address"""
        if self.transport:
            data = json.dumps(message).encode('utf-8')
            self.transport.sendto(data, addr)
            logger.debug(f"Sent message to {addr}: {message}")

    def broadcast_message(self, message: dict, port: int = 49476):
        """Broadcast a message to all subscribed clients (or network if no subscribers)"""
        logger.debug(f"broadcast_message ENTRY - subscribers: {len(self.subscribers)}")
        if self.transport:
            data = json.dumps(message).encode('utf-8')

            if self.subscribers:
                # Send to each subscriber
                dead_subscribers = set()
                for addr in self.subscribers:
                    try:
                        logger.debug(f"Sending to {addr}...")
                        self.transport.sendto(data, addr)
                        logger.debug(f"Sent to {addr} OK")
                    except Exception as e:
                        logger.error(f"Failed to send to {addr}: {e}")
                        dead_subscribers.add(addr)

                # Clean up dead subscribers
                if dead_subscribers:
                    self.subscribers -= dead_subscribers
                    logger.warning(f"Removed {len(dead_subscribers)} dead subscribers")

                logger.debug(f"Sent message to {len(self.subscribers)} subscribers")
            else:
                # No subscribers yet, broadcast to network
                logger.debug("Broadcasting to network (no subscribers)")
                self.transport.sendto(data, ('<broadcast>', port))
                logger.debug("Broadcast to network complete")
        else:
            logger.error("broadcast_message called but transport is None!")
        logger.debug("broadcast_message EXIT")

    def stop(self):
        """Clean up sensor tasks"""
        for task in self.sensor_tasks:
            task.cancel()