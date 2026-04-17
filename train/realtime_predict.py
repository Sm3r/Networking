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
from matplotlib.ticker import MultipleLocator, AutoMinorLocator

try:
    from train.network import LSTM
    from train.constants import BIN_SIZE
except ImportError:
    from network import LSTM
    from constants import BIN_SIZE

DATA_DIR = Path(__file__).parent.parent / "data"
logger = logging.getLogger('networking')

def realtime_plot_worker(plot_queue):
    plt.ion() 
    fig, ax = plt.subplots(figsize=(10, 5))
    
    line_actual, = ax.plot([], [], label='Actual Traffic (Bytes)', color='blue', marker='o', markersize=4)
    line_pred, = ax.plot([], [], label='Predicted Traffic (Bytes)', color='red', linestyle='--', marker='x', markersize=4)
    
    ax.set_title("Live Network Traffic Forecast")
    ax.set_xlabel("Virtual Simulation Timestamp")
    ax.set_ylabel(f"Bytes per {BIN_SIZE} Timestamps Bin")
    ax.legend(loc='upper left')
    ax.xaxis.set_major_locator(MultipleLocator(BIN_SIZE * 2))
    ax.xaxis.set_minor_locator(MultipleLocator(BIN_SIZE))
    ax.grid(True, which='both', linestyle=':', alpha=0.7)
    fig.tight_layout()
    plt.show(block=False)

    times, actuals, preds = [], [], []
    times_actual, times_pred = [], []
    MAX_POINTS = 50 

    while True:
        try:
            # Read data from the predictor thread
            data = plot_queue.get(timeout=0.1)
            
            # A tuple of Nones acts as our kill switch when the simulation ends
            if data == (None, None, None):
                break
                
            t, act, pred = data
            
            if act is not None:
                times_actual.append(t)
                actuals.append(act)
                times_actual = times_actual[-MAX_POINTS:]
                actuals = actuals[-MAX_POINTS:]
            
            if pred is not None:
                times_pred.append(t)
                preds.append(pred)
                times_pred = times_pred[-MAX_POINTS:]
                preds = preds[-MAX_POINTS:]
            
            line_actual.set_data(times_actual, actuals)
            line_pred.set_data(times_pred, preds)
            
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
        self.live_sequence = deque([0.0] * self.SEQ_LENGTH, maxlen=self.SEQ_LENGTH)

    def run(self):
        logger.info("Live Predictor thread started.")
        current_bin_sum = 0
        current_bin = None

        with torch.no_grad():
            while not self._stop_event.is_set():

                while True:
                    try:
                        packet = self.packet_queue.get_nowait()
                        packet_vt = packet.virtual_timestamp
                        packet_bin = int(packet_vt // BIN_SIZE) * BIN_SIZE
                        
                        # If we've moved to a new bin, process the previous bin
                        if current_bin is not None and packet_bin > current_bin:
                            scaled_input = self.scaler.transform([[current_bin_sum]])
                            self.live_sequence.append(scaled_input[0][0])
                            
                            seq_tensor = torch.tensor(self.live_sequence, dtype=torch.float32).view(1, self.SEQ_LENGTH, 1)
                            scaled_prediction = self.model(seq_tensor)
                            real_prediction = self.scaler.inverse_transform(scaled_prediction.numpy())[0][0]
                            
                            formatted_time = self.simulation._format_time_pretty(current_bin)
                            logger.info(f"{formatted_time} Past 2 timesteps: {current_bin_sum} B | Predicted NEXT 2 timesteps: {real_prediction:.0f} B\n")
                            
                            # Plot actual value for the current bin
                            if self.plot_queue is not None:
                                self.plot_queue.put((current_bin, current_bin_sum, None))
                            
                            # Plot prediction for the next bin (at the timestamp of that bin)
                            if self.plot_queue is not None:
                                self.plot_queue.put((packet_bin, None, real_prediction))
                            
                            current_bin_sum = 0
                        
                        current_bin = packet_bin
                        current_bin_sum += int(packet.length)
                    except queue.Empty:
                        break
                    except AttributeError:
                        continue
                
                self._stop_event.wait(0.01)

    def stop(self):
        logger.info("Stopping Live Predictor thread...")
        self._stop_event.set()
        self.join(timeout=5)