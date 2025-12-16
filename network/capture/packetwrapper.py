from typing import Any

class PacketWrapper:
    """
    Wrapper for pyshark packets
    """
    def __init__(self, packet: Any, virtual_timestamp: float, time_of_day: float):
        """
        Extract information from a pyshark packet

        Attributes:
            packet (Any): a pyshark packet
            virtual_timestamp (float): the simulation time of the captured packet
            time_of_day (float): the simulation time of the day of the captured packet
        """
        self.real_timestamp = packet.sniff_timestamp
        self.virtual_timestamp = virtual_timestamp
        self.time_of_day = time_of_day
        self.protocols = packet.frame_info.protocols
        self.length = packet.length
        self.src_ip = self.src_port = self.dst_ip = self.dst_port = 'N/A'

        if 'IP' in packet:
            self.src_ip = packet.ip.src
            self.dst_ip = packet.ip.dst

        if 'TCP' in packet:
            self.src_port = packet.tcp.srcport
            self.dst_port = packet.tcp.dstport
        elif 'UDP' in packet:
            self.src_port = packet.udp.srcport
            self.dst_port = packet.udp.dstport

    def to_string(self) -> str:
        """
        Return a string representation of the packet with the csv format

        Returns:
            str: the formatted string with the packet info
        """
        return (
            f"{self.virtual_timestamp:.4f},{self.time_of_day:.4f},{self.real_timestamp},{self.protocols},"
            f"{self.src_ip},{self.dst_ip},{self.src_port},{self.dst_port},{self.length}\n"
        )
