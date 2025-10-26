#!/usr/bin/env python3
"""
Inference script for making predictions using the trained model.
Usage: python prediction/predict.py --csv-path <path_to_data.csv> [options]
"""
import numpy as np
import tensorflow as tf
import argparse
import pandas as pd
from pathlib import Path

from model import NetworkTrafficPredictor
from datapreparation import load_and_prepare_data, bin_timestamps_and_aggregate_traffic
from plot import plot_all_ips_predictions, plot_total_traffic_by_time


def load_trained_model(model_path='best_model.keras'):
    """
    Load a trained model from disk.
    
    Args:
        model_path: Path to the saved model file
        
    Returns:
        NetworkTrafficPredictor: Loaded predictor instance
    """
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    print(f"📦 Loading model from {model_path}...")
    predictor = NetworkTrafficPredictor()
    predictor.model = tf.keras.models.load_model(model_path)
    print("✅ Model loaded successfully!")
    
    return predictor


def predict_on_new_data(model_path='best_model.keras', 
                       csv_path='datasetx.csv',
                       bin_size=1.0,
                       sequence_length=20,
                       output_prefix='predictions'):
    """
    Make predictions on new data using the trained model.
    
    Args:
        model_path: Path to saved model
        csv_path: Path to CSV data
        bin_size: Time bin size for aggregation
        sequence_length: Sequence length (must match training)
        output_prefix: Prefix for output files
    """
    print("=" * 60)
    print("NETWORK TRAFFIC PREDICTION - INFERENCE")
    print("=" * 60)
    print(f"Model: {model_path}")
    print(f"Data: {csv_path}")
    print(f"Sequence length: {sequence_length}")
    print(f"Time bin size: {bin_size}")
    print("=" * 60)
    
    # Load and prepare data
    print("\n📊 Loading data...")
    data = load_and_prepare_data(csv_path)
    aggregated_data = bin_timestamps_and_aggregate_traffic(data, bin_size=bin_size)
    
    print(f"Data shape: {aggregated_data.shape}")
    print(f"Unique IPs: {aggregated_data['ip'].nunique()}")
    print(f"Time bins: {aggregated_data['time_bin'].nunique()}")
    
    # Load trained model
    predictor = load_trained_model(model_path)
    predictor.sequence_length = sequence_length
    
    # Prepare sequences
    print("\n🔄 Preparing sequences...")
    X, y, ip_columns, y_time_bins = predictor.prepare_sequences(aggregated_data)
    
    print(f"X shape: {X.shape}, y shape: {y.shape}")
    print(f"Number of IPs: {len(ip_columns)}")
    
    # Make predictions
    print("\n🔮 Making predictions...")
    predictions = predictor.predict(X, batch_size=32)
    
    # Calculate metrics
    print("\n📈 Calculating metrics...")
    y_actual = predictor.scaler.inverse_transform(y)
    y_actual = np.maximum(y_actual, 0)
    
    mse = np.mean((y_actual - predictions) ** 2)
    mae = np.mean(np.abs(y_actual - predictions))
    rmse = np.sqrt(mse)
    
    print(f"\n{'='*50}")
    print("📊 PREDICTION METRICS")
    print(f"{'='*50}")
    print(f"  MSE:  {mse:.2f}")
    print(f"  MAE:  {mae:.2f}")
    print(f"  RMSE: {rmse:.2f}")
    print(f"{'='*50}")
    
    # Per-IP metrics
    per_ip_mae = np.mean(np.abs(y_actual - predictions), axis=0)
    ip_errors = sorted(zip(ip_columns, per_ip_mae), key=lambda x: x[1], reverse=True)
    
    print(f"\n🔍 Top 10 IPs by prediction error:")
    for i, (ip, error) in enumerate(ip_errors[:10], 1):
        print(f"  {i:2d}. {ip:15s}: MAE={error:.2f}")
    
    # Save predictions and actuals
    print(f"\n💾 Saving results...")
    predictions_df = pd.DataFrame(predictions, columns=ip_columns)
    predictions_df['time_bin'] = y_time_bins
    predictions_df.to_csv(f'{output_prefix}_predictions.csv', index=False)
    
    actuals_df = pd.DataFrame(y_actual, columns=ip_columns)
    actuals_df['time_bin'] = y_time_bins
    actuals_df.to_csv(f'{output_prefix}_actuals.csv', index=False)
    
    print(f"  ✓ {output_prefix}_predictions.csv")
    print(f"  ✓ {output_prefix}_actuals.csv")
    
    # Generate plots
    print(f"\n📈 Generating plots...")
    plot_all_ips_predictions(
        predictor.model, predictor.scaler, X, y, ip_columns, 
        y_time_bins, n_points=200,
        save_path=f'{output_prefix}_all_ips.png',
        precomputed_predictions=predictions
    )
    
    plot_total_traffic_by_time(
        predictor.model, predictor.scaler, X, y, y_time_bins,
        n_points=200,
        save_path=f'{output_prefix}_total_traffic.png',
        precomputed_predictions=predictions
    )
    
    print(f"  ✓ {output_prefix}_all_ips.png")
    print(f"  ✓ {output_prefix}_total_traffic.png")
    
    print(f"\n✅ Prediction complete!")
    print(f"{'='*60}")
    
    return predictions, y_actual, ip_columns, y_time_bins





def main():
    parser = argparse.ArgumentParser(
        description='Make predictions using trained network traffic model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prediction/predict.py
  python prediction/predict.py --csv-path new_data.csv
  python prediction/predict.py --model-path my_model.keras
  python prediction/predict.py --output-prefix results/test1
        """
    )
    
    parser.add_argument('--model-path', type=str, default='best_model.keras',
                       help='Path to trained model (default: best_model.keras)')
    parser.add_argument('--csv-path', type=str, default='datasetx.csv',
                       help='Path to CSV data (default: datasetx.csv)')
    parser.add_argument('--bin-size', type=float, default=1.0,
                       help='Time bin size (default: 1.0)')
    parser.add_argument('--sequence-length', type=int, default=20,
                       help='Sequence length - MUST match training (default: 20)')
    parser.add_argument('--output-prefix', type=str, default='predictions',
                       help='Prefix for output files (default: predictions)')
    
    args = parser.parse_args()
    
    try:
        predict_on_new_data(
            model_path=args.model_path,
            csv_path=args.csv_path,
            bin_size=args.bin_size,
            sequence_length=args.sequence_length,
            output_prefix=args.output_prefix
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())