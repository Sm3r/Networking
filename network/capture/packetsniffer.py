import os
import datetime
import threading
import logging
import pyshark
import time
import queue
from typing import Any, TextIO, List
from simulation.simulation import Simulation
from capture.packetwrapper import PacketWrapper
from capture.packetlogger import PacketLogger

logger = logging.getLogger('networking')

class PacketSniffer(threading.Thread):
    """
    Creates a thread used to capture network traffic and save it into a file pcap
    """
    def __init__(self, interface: str = 'lo', simulation: Simulation = None):
        super().__init__()
        self.interface: str = interface
        self.simulation: Simulation = simulation
        self._stop_event = threading.Event()
        self.capture = None

        self._buffer = queue.SimpleQueue()
        self._logger = PacketLogger(self.get_packets)


    def _wrap_packet(self, packet: Any):
        """
        Callback used to wrap each packet with custom information

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
            packet = packet,
            virtual_timestamp = t,
            time_of_day = time_of_day
        )

        # Add packet info to buffer
        self._buffer.put(wrapper)
    
    def run(self):
        """
        Main thread function which runs the network capture and store all the data that should be logged
        """
        logger.debug(f"Listening to interface {self.interface}...\n")
        self.capture = pyshark.LiveCapture(
            interface = self.interface
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
                
            # self.capture.apply_on_packets(self._wrap_packet, timeout=5)
        except Exception as e:
            logger.error(f"Forced end of network capture: {e}\n")
        finally:
            if self.capture and self.capture.is_live():
                self.capture.close()

            # Clear used data
            self.capture = None

    def get_packets(self, amount: int = 10) -> List[PacketWrapper]:
        """
        Pops and returns at most the specified amount of packets from the buffer

        Returns:
            List[PacketWrapper]: a list of packets
        """
        packets = []
        for i in range(amount):
            try:
                packets.append(self._buffer.get_nowait())
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
        if self.capture == None:
            logger.warning("Network capture not started!\n")
            return

        logger.info("Stopping file capture...\n")
        self._stop_event.set()
        self._logger.stop_log()

        # Wait for capture to complete
        self.join()
