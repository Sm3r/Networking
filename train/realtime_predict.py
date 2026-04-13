import threading
import multiprocessing as mp
import queue
import torch
import numpy as np
import joblib
from collections import deque
from pathlib import Path
import logging

import matplotlib.pyplot as plt

from train.network import LSTM

DATA_DIR = Path(__file__).parent.parent / "data"
logger = logging.getLogger('networking')

def realtime_plot_worker(plot_queue):
    plt.ion() 
    fig, ax = plt.subplots(figsize=(10, 5))
    
    line_actual, = ax.plot([], [], label='Actual Traffic (Bytes)', color='blue', marker='o', markersize=4)
    line_pred, = ax.plot([], [], label='Predicted Traffic (Bytes)', color='red', linestyle='--', marker='x', markersize=4)
    
    ax.set_title("Live Network Traffic Forecast")
    ax.set_xlabel("Simulation Time (Seconds)")
    ax.set_ylabel("Bytes per 2 Timestamps Bin")
    ax.legend(loc='upper right')
    ax.grid(True, linestyle=':', alpha=0.7)
    fig.tight_layout()
    plt.show(block=False)

    times, actuals, preds = [], [], []
    MAX_POINTS = 50 

    while True:
        try:
            # Read data from the predictor thread
            data = plot_queue.get(timeout=0.1)
            
            # A tuple of Nones acts as our kill switch when the simulation ends
            if data == (None, None, None):
                break
                
            t, act, pred = data
            
            times.append(t)
            actuals.append(act)
            preds.append(pred)
            
            times = times[-MAX_POINTS:]
            actuals = actuals[-MAX_POINTS:]
            preds = preds[-MAX_POINTS:]
            
            line_actual.set_data(times, actuals)
            line_pred.set_data(times, preds)
            
            ax.relim()
            ax.autoscale_view()
            fig.canvas.draw()
            fig.canvas.flush_events()
            
        except queue.Empty:
            # Keep the GUI responsive even if no new data arrives
            plt.pause(0.01)
            
    plt.ioff()
    plt.close(fig)


class LivePredictor(threading.Thread):
    def __init__(self, sniffer, simulation, plot_queue=None):
        super().__init__()
        self.sniffer = sniffer
        self.simulation = simulation
        self.plot_queue = plot_queue
        self._stop_event = threading.Event()

        self.packet_queue = self.sniffer.register_subscriber()
        
        logger.info("Initializing ML Predictor...\n")
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
        start_time = self.simulation.get_time()

        with torch.no_grad():
            while not self._stop_event.is_set():

                while True:
                    try:
                        packet = self.packet_queue.get_nowait()
                        current_bin_sum += int(packet.length)
                    except queue.Empty:
                        break
                    except AttributeError:
                        continue
                
                current_sim_time = self.simulation.get_time()
                
                if current_sim_time - start_time >= self.BIN_DURATION:
                    scaled_input = self.scaler.transform([[current_bin_sum]])
                    self.live_sequence.append(scaled_input[0][0])
                    
                    seq_tensor = torch.tensor(self.live_sequence, dtype=torch.float32).view(1, self.SEQ_LENGTH, 1)
                    scaled_prediction = self.model(seq_tensor)
                    real_prediction = self.scaler.inverse_transform(scaled_prediction.numpy())[0][0]
                    
                    formatted_time = self.simulation._format_time_pretty(current_sim_time)
                    logger.info(f"[{formatted_time}] Past 2 timesteps: {current_bin_sum} B | Predicted NEXT 2 timesteps: {real_prediction:.0f} B\n")
                    if self.plot_queue is not None:
                        self.plot_queue.put((current_sim_time, current_bin_sum, real_prediction))
                    
                    current_bin_sum = 0
                    start_time += self.BIN_DURATION
                
                self._stop_event.wait(0.01)

    def stop(self):
        logger.info("Stopping Live Predictor thread...")
        self._stop_event.set()
        self.join(timeout=5)