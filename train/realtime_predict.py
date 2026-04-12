import threading
import torch
import numpy as np
import joblib
from collections import deque
from pathlib import Path
import logging

from train.network import LSTM

DATA_DIR = Path(__file__).parent.parent / "data"
logger = logging.getLogger('networking')

class LivePredictor(threading.Thread):
    def __init__(self, sniffer, simulation):
        super().__init__()
        self.sniffer = sniffer
        self.simulation = simulation
        self._stop_event = threading.Event()
        
        logger.info("Initializing ML Predictor...")
        self.scaler = joblib.load(DATA_DIR / "scaler.joblib")
        self.model = LSTM()
        self.model.load_state_dict(torch.load("model_LSTM.pth", map_location=torch.device('cpu')))
        self.model.eval()

        self.SEQ_LENGTH = 30
        self.BIN_DURATION = 2.0
        self.live_sequence = deque([0.0] * self.SEQ_LENGTH, maxlen=self.SEQ_LENGTH)

    def run(self):
        logger.info("Live Predictor thread started.")
        current_bin_sum = 0
        
        # Sync with the simulation's virtual clock
        start_time = self.simulation.get_time()

        with torch.no_grad():
            while not self._stop_event.is_set():
                # 1. Consume packets
                packets = self.sniffer.get_packets(amount=50)
                for wrapper in packets:
                    try:
                        current_bin_sum += int(wrapper.packet.length)
                    except AttributeError:
                        continue
                
                # 2. Check virtual clock instead of real-world time
                current_sim_time = self.simulation.get_time()
                
                if current_sim_time - start_time >= self.BIN_DURATION:
                    # Scale and predict
                    scaled_input = self.scaler.transform([[current_bin_sum]])
                    self.live_sequence.append(scaled_input[0][0])
                    
                    seq_tensor = torch.tensor(self.live_sequence, dtype=torch.float32).view(1, self.SEQ_LENGTH, 1)
                    scaled_prediction = self.model(seq_tensor)
                    real_prediction = self.scaler.inverse_transform(scaled_prediction.numpy())
                    
                    formatted_time = self.simulation._format_time_pretty(current_sim_time)
                    print(f"[{formatted_time}] Past 2s: {current_bin_sum} B | Predicted NEXT 2s: {real_prediction[0][0]:.0f} B")
                    
                    current_bin_sum = 0
                    start_time += self.BIN_DURATION
                
                # Tiny sleep to avoid locking the CPU
                self._stop_event.wait(0.01)

    def stop(self):
        logger.info("Stopping Live Predictor thread...")
        self._stop_event.set()
        self.join(timeout=5)