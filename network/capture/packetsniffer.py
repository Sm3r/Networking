import os
import datetime
import threading
import logging
import pyshark
import queue
from typing import Any, List
from simulation.simulation import Simulation
from capture.packetwrapper import PacketWrapper
from capture.packetlogger import PacketLogger

logger = logging.getLogger('networking')

class PacketSniffer(threading.Thread):
    """
    Creates a thread used to capture network traffic and save it into a file pcap.
    Uses a Publish-Subscribe pattern to safely distribute packets to multiple consumers.
    """
    def __init__(self, interface: str = 'lo', simulation: Simulation = None):
        super().__init__()
        self.interface: str = interface
        self.simulation: Simulation = simulation
        self._stop_event = threading.Event()
        self.capture = None

        # --- Publish/Subscribe Setup ---
        self._subscribers = []
        
        # Register a dedicated queue for the internal CSV logger
        self._logger_queue = self.register_subscriber()
        self._logger = PacketLogger(self.get_logger_packets)

    def register_subscriber(self) -> queue.SimpleQueue:
        """
        Creates and returns a dedicated queue for a new consumer.
        Any new packet captured will be copied into this queue.
        """
        new_queue = queue.SimpleQueue()
        self._subscribers.append(new_queue)
        return new_queue

    def _wrap_packet(self, packet: Any):
        """
        Callback used to wrap each packet with custom information.
        Broadcasts the wrapped packet to all registered subscriber queues.

        Attributes:
            packet(Any): the pyshark default packet
        """
        # Only process packets that have IP layer
        if 'IP' not in packet:
            return
            
        # Get packet info
        t = self.simulation.get_time()
        time_of_day = self.simulation.get_time_of_day()
        wrapper = PacketWrapper(
            packet=packet,
            virtual_timestamp=t,
            time_of_day=time_of_day
        )

        # Broadcast packet info to ALL registered queues
        for sub_queue in self._subscribers:
            sub_queue.put(wrapper)
    
    def run(self):
        """
        Main thread function which runs the network capture and stores all the data that should be logged
        """
        logger.debug(f"Listening to interface {self.interface}...\n")
        self.capture = pyshark.LiveCapture(
            interface=self.interface,
            bpf_filter="net 10.0.0.0 mask 255.255.255.0 and not icmp" # Filter packets not sent by mininet hosts
        )

        try:
            # Save wrapped packets
            while True:
                for packet in self.capture.sniff_continuously():
                    if self._stop_event.is_set():
                        break
                    self._wrap_packet(packet)
                if self._stop_event.is_set():
                    break
        except Exception as e:
            logger.error(f"Forced end of network capture: {e}\n")
        finally:
            if self.capture and self.capture.is_live():
                self.capture.close()

            # Clear used data
            self.capture = None

    def get_logger_packets(self, amount: int = 10) -> List[PacketWrapper]:
        """
        Pops and returns at most the specified amount of packets from the internal logger's queue.

        Returns:
            List[PacketWrapper]: a list of packets
        """
        packets = []
        for i in range(amount):
            try:
                packets.append(self._logger_queue.get_nowait())
            except queue.Empty:
                break
        return packets

    def start_capture(self, output_filename: str):
        """
        Start a live network capture

        Attributes:
            output_filename(str): the path to the output csv file
        """
        # Check file path
        if not output_filename:
            logger.error("Network capture output file path not specified!\n")
            return

        # Generate file name
        filename = output_filename + "-" + datetime.datetime.now().isoformat() + ".csv"

        # Check if file exists
        if os.path.exists(filename):
            logger.error(f"File {filename} already exists. Aborting!")
            raise FileExistsError

        # Start capture
        logger.info(f"Starting file capture to {filename}...\n")
        self._logger.start_log(filename)
        self.start()

    def stop_capture(self):
        """
        Stop the live capture
        """
        # Check if network capture was started
        if self.capture is None:
            logger.warning("Network capture not started!\n")
            return

        logger.info("Stopping file capture...\n")
        self._stop_event.set()

        # Force-unblock `sniff_continuously()` if it is waiting for packets.
        try:
            if self.capture and self.capture.is_live():
                self.capture.close()
        except Exception:
            pass

        self._logger.stop_log()

        # Wait for capture to complete
        self.join(timeout=5)
        if self.is_alive():
            logger.warning("Capture thread did not terminate in time\n")