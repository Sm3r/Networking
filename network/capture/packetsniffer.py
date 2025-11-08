import os
import datetime
import threading
import logging
import pyshark
import time
from typing import Any, TextIO
from simulation.simulation import Simulation
from capture.packetwrapper import PacketWrapper

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
        self._lock = threading.Lock()
        self.output_file: str = None
        self.csv_handle: TextIO = None
        self.capture = None

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

        # Write to csv
        with self._lock:
            if self.csv_handle and not self.csv_handle.closed:
                self.csv_handle.write(wrapper.to_string())
    
    def _close_csv(self):
        """
        Close csv output file
        """
        with self._lock:
            if self.csv_handle and not self.csv_handle.closed:
                self.csv_handle.close()
                logger.debug(f"{self.output_file} closed\n")

    def run(self):
        """
        Main thread function which runs the network capture and store all the data inside the output file
        """
        # TODO: Notify main threads that an exception has occured
        # Check file path
        if not self.output_file:
            logger.error("Network capture output file path not specified!\n")
            return

        # Create csv output file
        try:
            self.csv_handle = open(self.output_file, 'w')
            header = "virtual_timestamp,time_of_day,real_timestamp,protocols,src_ip,dst_ip,src_port,dst_port,length\n"
            self.csv_handle.write(header)
            logger.debug(f"{self.output_file} created\n")
        except IOError as e:
            logger.error(f"Error while opening {self.output_file}: {e}\n")
            return

        logger.debug(f"Listening to interface {self.interface}...\n")
        self.capture = pyshark.LiveCapture(
            interface = self.interface
        )

        try:
            # Save wrapped packets
            for packet in self.capture.sniff_continuously():
                if self._stop_event.is_set():
                    break
                self._wrap_packet(packet)
            # self.capture.apply_on_packets(self._wrap_packet, timeout=5)
        except Exception as e:
            logger.error(f"Forced end of network capture: {e}\n")
        finally:
            time.sleep(3)
            if self.capture and self.capture.is_live():
                self.capture.close()
            self._close_csv()

            # Clear used data
            self.capture = None
            self.output_file = None

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
        self.output_file = output_filename + "-" + datetime.datetime.now().isoformat() + ".csv"

        # Check if file exists
        if os.path.exists(self.output_file):
            logger.error(f"File {self.output_file} already exists. Aborting!")
            raise FileExistsError

        # Start capture
        logger.info(f"Starting file capture to {self.output_file}...\n")
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

        # Wait for capture to complete
        self.join()
