#!/usr/bin/env python3
"""
Training script for network traffic prediction model.
"""
import numpy as np
import tensorflow as tf
import argparse
import sys

from model import NetworkTrafficPredictor
from datapreparation import load_and_prepare_data, bin_timestamps_and_aggregate_traffic
from plot import plot_all_ips_predictions, plot_total_traffic_by_time


def main():
    parser = argparse.ArgumentParser(description='Train network traffic LSTM model')
    parser.add_argument('--batch-size', '-b', type=int, default=64, 
                       help='Training batch size')
    parser.add_argument('--epochs', '-e', type=int, default=150, 
                       help='Number of training epochs')
    parser.add_argument('--sequence-length', type=int, default=30,
                       help='Number of time steps to look back (increased for better context)')
    parser.add_argument('--lstm-units', type=int, default=128,
                       help='Number of units in LSTM layers')
    parser.add_argument('--dropout-rate', type=float, default=0.2,
                       help='Dropout rate')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                       help='Learning rate')
    parser.add_argument('--bin-size', type=float, default=5.0,
                       help='Time bin size for aggregating traffic (larger = less sparse)')
    parser.add_argument('--csv-path', type=str, default='datasetx.csv',
                       help='Path to the CSV dataset')
    parser.add_argument('--min-traffic', type=int, default=5000,
                       help='Minimum total traffic per IP to include (filters noise)')
    parser.add_argument('--use-bidirectional', action='store_true',
                       help='Use bidirectional LSTM')
    parser.add_argument('--include-time-features', action='store_true', default=True,
                       help='Include temporal features in the model')
    args = parser.parse_args()

    print("=" * 70)
    print("NETWORK TRAFFIC PREDICTION - TRAINING")
    print("=" * 70)
    print(f"Dataset: {args.csv_path}")
    print(f"Sequence length: {args.sequence_length}")
    print(f"LSTM units: {args.lstm_units}")
    print(f"Dropout: {args.dropout_rate}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Batch size: {args.batch_size}")
    print(f"Epochs: {args.epochs}")
    print(f"Time bin size: {args.bin_size}s")
    print(f"Min traffic threshold: {args.min_traffic}")
    print(f"Bidirectional LSTM: {args.use_bidirectional}")
    print(f"Include time features: {args.include_time_features}")
    print("=" * 70)
    
    # Load and prepare data
    print("\n📊 Loading data...")
    data = load_and_prepare_data(args.csv_path)
    print(f"✓ Loaded {len(data)} packets after filtering")
    
    aggregated_data = bin_timestamps_and_aggregate_traffic(
        data, 
        bin_size=args.bin_size,
        min_traffic_threshold=args.min_traffic
    )
    
    print(f"\n📈 Data Statistics:")
    print(f"  Data shape: {aggregated_data.shape}")
    print(f"  Unique IPs: {aggregated_data['ip'].nunique()}")
    print(f"  Time bins: {aggregated_data['time_bin'].nunique()}")
    print(f"  Time range: {aggregated_data['time_bin'].min():.1f}s to {aggregated_data['time_bin'].max():.1f}s")
    print(f"  Traffic size - Min: {aggregated_data['total_traffic_size'].min():.0f}, "
          f"Max: {aggregated_data['total_traffic_size'].max():.0f}, "
          f"Mean: {aggregated_data['total_traffic_size'].mean():.2f}")
    
    # Show top IPs by traffic
    print(f"\n🌐 Top 10 IPs by total traffic:")
    top_ips = aggregated_data.groupby('ip')['total_traffic_size'].sum().sort_values(ascending=False).head(10)
    for ip, traffic in top_ips.items():
        print(f"  {ip}: {traffic:,.0f} bytes")
    
    # Initialize predictor
    print("\n🔧 Initializing predictor...")
    predictor = NetworkTrafficPredictor(
        sequence_length=args.sequence_length,
        lstm_units=args.lstm_units,
        dropout_rate=args.dropout_rate,
        learning_rate=args.learning_rate,
        use_bidirectional=args.use_bidirectional
    )
    
    # Prepare sequences
    print("\n🔄 Preparing sequences...")
    X, y, ip_columns, y_time_bins = predictor.prepare_sequences(
        aggregated_data,
        include_time_features=args.include_time_features
    )
    
    print(f"✓ X shape: {X.shape}, y shape: {y.shape}")
    print(f"✓ Number of IPs (outputs): {len(ip_columns)}")
    print(f"✓ Features per timestep: {X.shape[2]}")
    
    if X.shape[0] < 100:
        print(f"\n⚠️  WARNING: Only {X.shape[0]} sequences available. Consider:")
        print("   - Decreasing bin_size (currently {args.bin_size}s)")
        print("   - Decreasing sequence_length (currently {args.sequence_length})")
        print("   - Running a longer simulation to generate more data")
        sys.exit(1)
    
    # Time-based split: 80% train, 20% test
    split_idx = int(X.shape[0] * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    y_test_time_bins = y_time_bins[split_idx:]

    print(f"\n📊 Data Split:")
    print(f"  Train: {X_train.shape[0]} sequences")
    print(f"  Test: {X_test.shape[0]} sequences")
    print(f"  Test time range: {y_test_time_bins.min():.1f}s to {y_test_time_bins.max():.1f}s")
    
    # Build and train model
    print("\n🏗️  Building model...")
    predictor.build_model(n_features=X.shape[2], n_output_features=len(ip_columns))
    print(predictor.model.summary())
    
    print(f"\n🚀 Training model...")
    print("=" * 70)
    history = predictor.train(X_train, y_train, epochs=args.epochs, batch_size=args.batch_size)
    
    # Evaluate model
    print("\n" + "=" * 70)
    print("📈 Evaluating model...")
    try:
        predictor.model = tf.keras.models.load_model('best_model.keras')
        print("✅ Loaded best model checkpoint")
    except Exception as e:
        print(f"⚠️  Using final training state (checkpoint load failed: {e})")

    metrics = predictor.evaluate_model(X_test, y_test, batch_size=64)
    
    print("\n" + "=" * 70)
    print("📊 TEST METRICS")
    print("=" * 70)
    print(f"  MSE:   {metrics['mse']:,.2f}")
    print(f"  MAE:   {metrics['mae']:,.2f}")
    print(f"  RMSE:  {metrics['rmse']:,.2f}")
    print(f"  MAPE:  {metrics['mape']:.2f}%")
    print("=" * 70)
    
    # Show per-IP performance
    print(f"\n📊 Per-IP Performance (Top 10 by MAE):")
    per_ip_df = list(zip(ip_columns, metrics['per_ip_mae']))
    per_ip_df.sort(key=lambda x: x[1], reverse=True)
    for ip, mae in per_ip_df[:10]:
        print(f"  {ip}: MAE = {mae:,.2f} bytes")
    
    # Generate predictions for visualization
    print("\n📊 Generating test predictions...")
    y_pred = predictor.predict(X_test, batch_size=64)
    y_actual = predictor.scaler.inverse_transform(y_test)
    
    # Save predictions
    import pandas as pd
    pred_df = pd.DataFrame(y_pred, columns=ip_columns)
    pred_df['time_bin'] = y_test_time_bins
    pred_df.to_csv('test_inference_predictions.csv', index=False)
    
    actual_df = pd.DataFrame(y_actual, columns=ip_columns)
    actual_df['time_bin'] = y_test_time_bins
    actual_df.to_csv('test_inference_actuals.csv', index=False)
    
    print("✅ Saved predictions to test_inference_predictions.csv")
    print("✅ Saved actuals to test_inference_actuals.csv")
    
    # Plot results
    print("\n📊 Generating plots...")
    try:
        plot_all_ips_predictions(
            model=None,
            scaler=predictor.scaler,
            X_test=X_test,
            y_test=y_test,
            ip_columns=ip_columns,
            y_time_bins=y_test_time_bins,
            n_points=200,
            save_path='all_ips_predictions.png',
            precomputed_predictions=y_pred
        )
        
        plot_total_traffic_by_time(
            model=None,
            scaler=predictor.scaler,
            X_test=X_test,
            y_test=y_test,
            y_time_bins=y_test_time_bins,
            n_points=200,
            save_path='total_traffic_by_time.png',
            precomputed_predictions=y_pred
        )
        print("✅ Plots generated successfully")
    except Exception as e:
        print(f"⚠️  Plot generation failed: {e}")
    
    print("\n" + "=" * 70)
    print("✅ TRAINING COMPLETE!")
    print("=" * 70)


if __name__ == '__main__':
    main()
