"""
Training script for network traffic prediction model.
"""
import numpy as np
import tensorflow as tf
import argparse

from model import NetworkTrafficPredictor
from datapreparation import load_and_prepare_data, bin_timestamps_and_aggregate_traffic
from plot import plot_all_ips_predictions, plot_total_traffic_by_time


def main():
    parser = argparse.ArgumentParser(description='Train network traffic GRU model')
    parser.add_argument('--batch-size', '-b', type=int, default=64, 
                       help='Training batch size')
    parser.add_argument('--epochs', '-e', type=int, default=200, 
                       help='Number of training epochs')
    parser.add_argument('--sequence-length', type=int, default=20,
                       help='Number of time steps to look back')
    parser.add_argument('--gru-units', type=int, default=128,
                       help='Number of units in GRU layers')
    parser.add_argument('--dropout-rate', type=float, default=0.3,
                       help='Dropout rate')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                       help='Learning rate')
    parser.add_argument('--bin-size', type=float, default=1.0,
                       help='Time bin size for aggregating traffic')
    parser.add_argument('--csv-path', type=str, default='datasetx.csv',
                       help='Path to the CSV dataset')
    args = parser.parse_args()

    print("=" * 60)
    print("NETWORK TRAFFIC PREDICTION - TRAINING")
    print("=" * 60)
    print(f"Dataset: {args.csv_path}")
    print(f"Sequence length: {args.sequence_length}")
    print(f"GRU units: {args.gru_units}")
    print(f"Dropout: {args.dropout_rate}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Batch size: {args.batch_size}")
    print(f"Epochs: {args.epochs}")
    print(f"Time bin size: {args.bin_size}")
    print("=" * 60)
    # Load and prepare data
    print("\n📊 Loading data...")
    data = load_and_prepare_data(args.csv_path)
    aggregated_data = bin_timestamps_and_aggregate_traffic(data, bin_size=args.bin_size)
    
    print(f"Data shape: {aggregated_data.shape}")
    print(f"Unique IPs: {aggregated_data['ip'].nunique()}")
    print(f"Time bins: {aggregated_data['time_bin'].nunique()}")
    
    # Initialize predictor
    print("\n🔧 Initializing predictor...")
    predictor = NetworkTrafficPredictor(
        sequence_length=args.sequence_length,
        gru_units=args.gru_units,
        dropout_rate=args.dropout_rate,
        learning_rate=args.learning_rate
    )
    
    # Prepare sequences
    print("\n🔄 Preparing sequences...")
    X, y, ip_columns, y_time_bins = predictor.prepare_sequences(aggregated_data)
    
    print(f"X shape: {X.shape}, y shape: {y.shape}")
    print(f"Number of IPs: {len(ip_columns)}")
    
    # Time-based split: 80% train, 20% test
    split_idx = int(X.shape[0] * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    y_test_time_bins = y_time_bins[split_idx:]

    print(f"\nTrain: {X_train.shape}, Test: {X_test.shape}")
    
    # Build and train model
    print("\n🏗️ Building model...")
    predictor.build_model(n_features=len(ip_columns))
    print(predictor.model.summary())
    
    print(f"\n🚀 Training model...")
    history = predictor.train(X_train, y_train, epochs=args.epochs, batch_size=args.batch_size)
    
    # Evaluate model
    print("\n📈 Evaluating model...")
    try:
        predictor.model = tf.keras.models.load_model('best_model.keras')
        print("✅ Loaded best model checkpoint")
    except Exception:
        print("⚠️ Using final training state")

    metrics = predictor.evaluate_model(X_test, y_test, batch_size=32)
    
    print("\n" + "=" * 50)
    print("📊 TEST METRICS")
    print("=" * 50)
    print(f"  MSE:  {metrics['mse']:.2f}")
    print(f"  MAE:  {metrics['mae']:.2f}")
    print(f"  RMSE: {metrics['rmse']:.2f}")
    
    # Per-IP errors
    per_ip_mae = metrics['per_ip_mae']
    ip_errors = sorted(zip(ip_columns, per_ip_mae), key=lambda x: x[1], reverse=True)
    
    print(f"\n🔍 Top 10 IPs by prediction error:")
    for i, (ip, error) in enumerate(ip_errors[:10], 1):
        print(f"  {i:2d}. {ip:15s}: MAE={error:.2f}")
    print("=" * 50)
    
    # Make predictions for plotting
    print("\n🔮 Generating predictions...")
    predictions = predictor.predict(X_test, batch_size=32)
    
    # Generate plots
    print("\n📈 Creating plots...")
    plot_all_ips_predictions(
        predictor.model, predictor.scaler, X_test, y_test, ip_columns, 
        y_test_time_bins, n_points=200,
        precomputed_predictions=predictions,
        save_path='all_ips_predictions.png'
    )
    
    plot_total_traffic_by_time(
        predictor.model, predictor.scaler, X_test, y_test, y_test_time_bins, 
        n_points=200,
        precomputed_predictions=predictions,
        save_path='total_traffic_by_time.png'
    )
    
    # Save scaler and IP columns for inference
    print("\n💾 Saving scaler and IP list...")
    import joblib
    joblib.dump(predictor.scaler, 'scaler.pkl')
    joblib.dump(ip_columns, 'ip_columns.pkl')
    
    print("\n✅ Training complete!")
    print("📁 Files generated:")
    print("  - best_model.keras")
    print("  - scaler.pkl")
    print("  - ip_columns.pkl")
    print("  - all_ips_predictions.png")
    print("  - total_traffic_by_time.png")


if __name__ == "__main__":
    main()