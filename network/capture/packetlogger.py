import os
import time
import threading
import logging

logger = logging.getLogger('networking')

class PacketLogger(threading.Thread):
    """
    Log network packets into a CSV file
    """
    def __init__(self, get_packets):
        super().__init__()
        self.output_file: str = None
        self.csv_handle: TextIO = None
        self.get_packets = get_packets

        self._stop_event = threading.Event()

    def _close_csv(self):
        """
        Close csv output file
        """
        if self.csv_handle and not self.csv_handle.closed:
            self.csv_handle.close()
            logger.debug(f"{self.output_file} closed\n")

    def run(self):
        """
        Main thread function which runs the packet logger and store all the data inside the output file
        """
        # Check file path
        if not self.output_file:
            logger.error("Network capture output file path not specified!\n")
            return

        while True:
            # Get packets to log from the sniffer
            packets = self.get_packets(amount = 100)
            if len(packets) > 0:
                for packet in packets:
                    if self.csv_handle and not self.csv_handle.closed:
                        self.csv_handle.write(packet.to_string())
            else:
                if self._stop_event.is_set():
                    break
                time.sleep(200 * 1e-3)

            # Wait a bit before writing again
            time.sleep(50 * 1e-3)


    def start_log(self, filename: str):
        """
        Start the packet logger thread

        Attributes:
            filename(str): the path to the output csv file
        """
        self.output_file = filename

        # Create csv output file
        try:
            self.csv_handle = open(self.output_file, 'w')
            header = "virtual_timestamp,time_of_day,real_timestamp,protocols,src_ip,dst_ip,src_port,dst_port,length\n"
            self.csv_handle.write(header)
            logger.debug(f"{self.output_file} created\n")
        except IOError as e:
            logger.error(f"Error while opening {self.output_file}: {e}\n")
            return
        
        self.start()
 
    def stop_log(self):
        """
        Stop the packet logger
        """
        self._stop_event.set()

        # Wait for logger to terminate
        self.join()
        self._close_csv()
