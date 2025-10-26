#!/usr/bin/env python3
"""
Real-time network traffic prediction system.

This module provides continuous prediction capabilities by maintaining
a sliding window of recent traffic data and making predictions as new
data arrives.
"""
import numpy as np
import pandas as pd
import tensorflow as tf
from pathlib import Path
from collections import deque
from datetime import datetime
import time
import argparse

from model import NetworkTrafficPredictor
from datapreparation import load_and_prepare_data, bin_timestamps_and_aggregate_traffic


class RealTimePredictor:
    """Real-time traffic prediction with sliding window."""
    
    def __init__(self, model_path='best_model.keras', sequence_length=20, bin_size=1.0):
        """
        Initialize real-time predictor.
        
        Args:
            model_path: Path to trained model
            sequence_length: Sequence length (must match training)
            bin_size: Time bin size in seconds
        """
        self.model_path = model_path
        self.sequence_length = sequence_length
        self.bin_size = bin_size
        
        # Load model
        self.predictor = self._load_model()
        
        # Initialize sliding window buffer
        self.window_buffer = None
        self.ip_columns = None
        self.current_time_bin = None
        self.predictions_log = []
        
        print(f"✅ Real-time predictor initialized")
        print(f"   Model: {model_path}")
        print(f"   Sequence length: {sequence_length}")
        print(f"   Bin size: {bin_size}s")
    
    def _load_model(self):
        """Load trained model."""
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        predictor = NetworkTrafficPredictor(sequence_length=self.sequence_length)
        predictor.model = tf.keras.models.load_model(self.model_path)
        print(f"📦 Model loaded from {self.model_path}")
        
        return predictor
    
    def initialize_from_historical_data(self, csv_path='datasetx.csv', lookback_bins=None, 
                                        start_from_middle=False):
        """
        Initialize the sliding window from historical data.
        
        Args:
            csv_path: Path to historical data
            lookback_bins: Number of recent bins to use (default: sequence_length)
            start_from_middle: If True, use middle section instead of end
        """
        if lookback_bins is None:
            lookback_bins = self.sequence_length
        
        print(f"\n📊 Initializing from historical data...")
        
        # Load and prepare data
        data = load_and_prepare_data(csv_path)
        aggregated = bin_timestamps_and_aggregate_traffic(data, bin_size=self.bin_size)
        
        # Prepare sequences to get IP columns and scaler
        X, y, ip_columns, time_bins = self.predictor.prepare_sequences(aggregated)
        self.ip_columns = ip_columns
        
        # Store the aggregated data for later use
        self.aggregated_data = aggregated
        
        # Get time bins for initialization
        unique_time_bins = sorted(aggregated['time_bin'].unique())
        
        if start_from_middle:
            # Use middle section for simulation
            middle_idx = len(unique_time_bins) // 2
            start_idx = max(0, middle_idx - lookback_bins)
            recent_time_bins = unique_time_bins[start_idx:start_idx + lookback_bins]
        else:
            # Use most recent bins
            recent_time_bins = unique_time_bins[-lookback_bins:]
        
        # Initialize window buffer with recent data
        window_data = []
        for time_bin in recent_time_bins:
            bin_data = aggregated[aggregated['time_bin'] == time_bin]
            traffic_vector = np.zeros(len(ip_columns))
            
            for idx, ip in enumerate(ip_columns):
                ip_traffic = bin_data[bin_data['ip'] == ip]['total_traffic_size'].sum()
                traffic_vector[idx] = ip_traffic
            
            window_data.append(traffic_vector)
        
        # Scale the window data
        window_array = np.array(window_data)
        self.window_buffer = deque(
            self.predictor.scaler.transform(window_array).tolist(),
            maxlen=self.sequence_length
        )
        
        self.current_time_bin = recent_time_bins[-1]
        
        print(f"✅ Initialized with {len(self.window_buffer)} time bins")
        print(f"   IP addresses tracked: {len(self.ip_columns)}")
        print(f"   Current time bin: {self.current_time_bin:.1f}s")
        
        return self
    
    def add_traffic_data(self, traffic_data):
        """
        Add new traffic data and update sliding window.
        
        Args:
            traffic_data: Dict mapping IP addresses to traffic sizes
                         e.g., {'10.0.0.1': 1500, '10.0.0.2': 3000}
        """
        if self.window_buffer is None:
            raise RuntimeError("Predictor not initialized. Call initialize_from_historical_data() first.")
        
        # Create traffic vector for all IPs
        traffic_vector = np.zeros(len(self.ip_columns))
        for idx, ip in enumerate(self.ip_columns):
            traffic_vector[idx] = traffic_data.get(ip, 0)
        
        # Scale the new data
        scaled_vector = self.predictor.scaler.transform(traffic_vector.reshape(1, -1))[0]
        
        # Add to sliding window
        self.window_buffer.append(scaled_vector)
        self.current_time_bin += self.bin_size
        
        return scaled_vector
    
    def predict_next_step(self):
        """
        Predict traffic for the next time step.
        
        Returns:
            dict: Predictions for each IP address
        """
        if self.window_buffer is None or len(self.window_buffer) < self.sequence_length:
            raise RuntimeError("Not enough data in buffer for prediction")
        
        # Prepare input sequence
        sequence = np.array(list(self.window_buffer)[-self.sequence_length:])
        X = sequence.reshape(1, self.sequence_length, -1)
        
        # Make prediction
        prediction_scaled = self.predictor.model.predict(X, verbose=0)
        prediction = self.predictor.scaler.inverse_transform(prediction_scaled)[0]
        
        # Ensure non-negative
        prediction = np.maximum(prediction, 0)
        
        # Create result dictionary
        result = {
            'time_bin': self.current_time_bin + self.bin_size,
            'timestamp': datetime.now().isoformat(),
            'predictions': {ip: float(pred) for ip, pred in zip(self.ip_columns, prediction)},
            'total_predicted': float(np.sum(prediction))
        }
        
        # Log prediction
        self.predictions_log.append(result)
        
        return result
    
    def get_predictions_dataframe(self):
        """Get all predictions as a DataFrame."""
        if not self.predictions_log:
            return pd.DataFrame()
        
        records = []
        for log in self.predictions_log:
            record = {'time_bin': log['time_bin'], 'timestamp': log['timestamp']}
            record.update(log['predictions'])
            record['total'] = log['total_predicted']
            records.append(record)
        
        return pd.DataFrame(records)
    
    def save_predictions(self, output_path='realtime_predictions.csv'):
        """Save predictions to CSV."""
        df = self.get_predictions_dataframe()
        df.to_csv(output_path, index=False)
        print(f"💾 Saved {len(df)} predictions to {output_path}")
        return output_path


def simulate_realtime_prediction(csv_path='datasetx.csv', 
                                 model_path='best_model.keras',
                                 sequence_length=20,
                                 bin_size=1.0,
                                 num_predictions=50,
                                 delay=0.1):
    """
    Simulate real-time prediction by streaming through historical data.
    
    Args:
        csv_path: Path to data
        model_path: Path to model
        sequence_length: Sequence length
        bin_size: Time bin size
        num_predictions: Number of predictions to make
        delay: Delay between predictions (seconds)
    """
    print("=" * 70)
    print("REAL-TIME TRAFFIC PREDICTION - SIMULATION MODE")
    print("=" * 70)
    
    # Initialize predictor
    predictor = RealTimePredictor(model_path, sequence_length, bin_size)
    predictor.initialize_from_historical_data(csv_path, start_from_middle=True)
    
    # Load full data for simulation
    print(f"\n🎬 Starting simulation with {num_predictions} predictions...")
    print(f"   Delay between predictions: {delay}s")
    print()
    
    data = load_and_prepare_data(csv_path)
    aggregated = bin_timestamps_and_aggregate_traffic(data, bin_size=bin_size)
    
    # Get time bins after initialization - use middle section for better data
    all_time_bins = sorted(aggregated['time_bin'].unique())
    
    # Use data from the middle of the dataset (more representative)
    middle_idx = len(all_time_bins) // 2
    start_idx = max(sequence_length, middle_idx - num_predictions // 2)
    end_idx = min(len(all_time_bins), start_idx + num_predictions)
    simulation_bins = all_time_bins[start_idx:end_idx]
    
    predictions = []
    actuals = []
    
    for i, time_bin in enumerate(simulation_bins, 1):
        # Get actual traffic for this time bin
        bin_data = aggregated[aggregated['time_bin'] == time_bin]
        actual_traffic = {}
        for ip in predictor.ip_columns:
            ip_traffic = bin_data[bin_data['ip'] == ip]['total_traffic_size'].sum()
            actual_traffic[ip] = ip_traffic
        
        # Make prediction before adding new data
        prediction = predictor.predict_next_step()
        predictions.append(prediction)
        
        # Add actual data to window
        predictor.add_traffic_data(actual_traffic)
        
        # Display progress
        pred_total = prediction['total_predicted']
        actual_total = sum(actual_traffic.values())
        error = abs(pred_total - actual_total)
        
        print(f"[{i:3d}/{num_predictions}] Time: {time_bin:7.1f}s | "
              f"Predicted: {pred_total:8.1f} | "
              f"Actual: {actual_total:8.1f} | "
              f"Error: {error:7.1f}")
        
        actuals.append({'time_bin': time_bin, 'total': actual_total})
        
        time.sleep(delay)
    
    # Calculate statistics
    print("\n" + "=" * 70)
    print("SIMULATION RESULTS")
    print("=" * 70)
    
    pred_totals = [p['total_predicted'] for p in predictions]
    actual_totals = [a['total'] for a in actuals]
    
    mae = np.mean(np.abs(np.array(pred_totals) - np.array(actual_totals)))
    rmse = np.sqrt(np.mean((np.array(pred_totals) - np.array(actual_totals)) ** 2))
    
    print(f"\nPrediction Accuracy:")
    print(f"  MAE (Mean Absolute Error):  {mae:.2f} bytes")
    print(f"  RMSE (Root Mean Squared):   {rmse:.2f} bytes")
    print(f"  Total predictions made:     {len(predictions)}")
    
    # Save results
    output_file = predictor.save_predictions()
    
    print(f"\n✅ Simulation complete!")
    print(f"📁 Results saved to: {output_file}")
    
    return predictor, predictions, actuals


def stream_live_predictions(model_path='best_model.keras',
                           sequence_length=20,
                           bin_size=1.0,
                           csv_path='datasetx.csv'):
    """
    Stream live predictions with manual data input.
    
    This is a framework for connecting to live network data sources.
    """
    print("=" * 70)
    print("REAL-TIME TRAFFIC PREDICTION - LIVE MODE")
    print("=" * 70)
    
    predictor = RealTimePredictor(model_path, sequence_length, bin_size)
    predictor.initialize_from_historical_data(csv_path)
    
    print("\n📡 Ready for live predictions")
    print("   Waiting for traffic data...")
    print("   (Press Ctrl+C to stop)\n")
    
    try:
        iteration = 0
        while True:
            iteration += 1
            
            # In production, replace this with actual network capture
            # Example: traffic_data = capture_network_traffic(bin_size)
            
            # For now, simulate with zeros (placeholder)
            traffic_data = {ip: 0 for ip in predictor.ip_columns}
            
            # Make prediction
            prediction = predictor.predict_next_step()
            
            # Display prediction
            print(f"[{iteration:4d}] Time: {prediction['time_bin']:7.1f}s | "
                  f"Predicted Total: {prediction['total_predicted']:8.1f} bytes")
            
            # In production, add actual captured data
            # predictor.add_traffic_data(traffic_data)
            
            time.sleep(bin_size)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping live predictions...")
        predictor.save_predictions('live_predictions.csv')
        print("✅ Predictions saved")


def main():
    parser = argparse.ArgumentParser(
        description='Real-time network traffic prediction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulate real-time prediction
  python prediction/realtime_predict.py --mode simulate --num-predictions 100
  
  # Simulate with custom delay
  python prediction/realtime_predict.py --mode simulate --delay 0.5
  
  # Live streaming mode (placeholder)
  python prediction/realtime_predict.py --mode live
        """
    )
    
    parser.add_argument('--mode', type=str, default='simulate',
                       choices=['simulate', 'live'],
                       help='Prediction mode (default: simulate)')
    parser.add_argument('--model-path', type=str, default='best_model.keras',
                       help='Path to trained model (default: best_model.keras)')
    parser.add_argument('--csv-path', type=str, default='datasetx.csv',
                       help='Path to CSV data (default: datasetx.csv)')
    parser.add_argument('--sequence-length', type=int, default=20,
                       help='Sequence length (default: 20)')
    parser.add_argument('--bin-size', type=float, default=1.0,
                       help='Time bin size (default: 1.0)')
    parser.add_argument('--num-predictions', type=int, default=50,
                       help='Number of predictions in simulation (default: 50)')
    parser.add_argument('--delay', type=float, default=0.1,
                       help='Delay between predictions in seconds (default: 0.1)')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'simulate':
            simulate_realtime_prediction(
                csv_path=args.csv_path,
                model_path=args.model_path,
                sequence_length=args.sequence_length,
                bin_size=args.bin_size,
                num_predictions=args.num_predictions,
                delay=args.delay
            )
        elif args.mode == 'live':
            stream_live_predictions(
                model_path=args.model_path,
                sequence_length=args.sequence_length,
                bin_size=args.bin_size,
                csv_path=args.csv_path
            )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
