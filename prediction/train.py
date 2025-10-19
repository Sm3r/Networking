import numpy as np
import tensorflow as tf
import argparse

from model import NetworkTrafficPredictor
from datapreparation import load_and_prepare_data, bin_timestamps_and_aggregate_traffic
from plot import plot_all_ips_predictions, plot_total_traffic_by_time

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Train/evaluate network traffic GRU model')
    parser.add_argument('--batch-size', '-b', type=int, default=64, 
                       help='Training batch size')
    parser.add_argument('--predict-batch-size', type=int, default=32, 
                       help='Batch size used for predict/evaluate')
    parser.add_argument('--epochs', '-e', type=int, default=100, 
                       help='Number of training epochs')
    parser.add_argument('--sequence-length', type=int, default=10,
                       help='Number of time steps to look back for prediction')
    parser.add_argument('--gru-units', type=int, default=64,
                       help='Number of units in GRU layers')
    parser.add_argument('--dropout-rate', type=float, default=0.2,
                       help='Dropout rate for regularization')
    parser.add_argument('--bin-size', type=float, default=1.0,
                       help='Time bin size for aggregating traffic')
    parser.add_argument('--csv-path', type=str, default='dataset.csv',
                       help='Path to the CSV dataset')
    args = parser.parse_args()

    print("=" * 60)
    print("NETWORK TRAFFIC PREDICTION MODEL TRAINING")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Dataset: {args.csv_path}")
    print(f"  Sequence length: {args.sequence_length}")
    print(f"  GRU units: {args.gru_units}")
    print(f"  Dropout rate: {args.dropout_rate}")
    print(f"  Training batch size: {args.batch_size}")
    print(f"  Prediction batch size: {args.predict_batch_size}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Time bin size: {args.bin_size}")
    print("=" * 60)

    # Load and prepare data
    print("\n📊 Loading and preparing data...")
    data = load_and_prepare_data(args.csv_path)
    aggregated_data = bin_timestamps_and_aggregate_traffic(data, bin_size=args.bin_size)
    
    print(f"Aggregated data shape: {aggregated_data.shape}")
    print(f"Unique IPs: {aggregated_data['ip'].nunique()}")
    print(f"Time range: {aggregated_data['time_bin'].min():.1f} - {aggregated_data['time_bin'].max():.1f}")
    
    # Initialize predictor
    predictor = NetworkTrafficPredictor(
        sequence_length=args.sequence_length, 
        gru_units=args.gru_units, 
        dropout_rate=args.dropout_rate
    )
    
    # Prepare sequences
    print("\n🔄 Preparing sequences for training...")
    X, y, ip_columns, y_time_bins = predictor.prepare_sequences(aggregated_data)
    
    print(f"Sequence data shape: X={X.shape}, y={y.shape}")
    print(f"Number of features (IPs): {len(ip_columns)}")
    
    # Time-based split: use the first 80% of time-ordered samples for training
    n_samples = X.shape[0]
    split_idx = int(n_samples * 0.8)

    X_train = X[:split_idx]
    y_train = y[:split_idx]
    X_test = X[split_idx:]
    y_test = y[split_idx:]

    split_time = y_time_bins[split_idx] if len(y_time_bins) > split_idx else None

    print(f"Training data: X_train={X_train.shape}, y_train={y_train.shape}")
    print(f"Test data: X_test={X_test.shape}, y_test={y_test.shape}")
    if split_time is not None:
        print(f"Time-based split boundary (first test time_bin): {split_time}")
    
    # Build and train model
    print("\n🏗️ Building GRU model...")
    predictor.build_model(n_features=len(ip_columns))
    print(predictor.model.summary())
    
    print(f"\n🚀 Training model for {args.epochs} epochs...")
    history = predictor.train(X_train, y_train, epochs=args.epochs, batch_size=args.batch_size)
    
    # Evaluate model
    print("\n📈 Evaluating model...")
    # If a best_model checkpoint exists, load it for evaluation
    try:
        # Load the full model saved in Keras native format (avoids HDF5 legacy warning)
        predictor.model = tf.keras.models.load_model('best_model.keras')
        print("✅ Loaded best model checkpoint for evaluation")
    except Exception:
        # fallback: if only weights (or older .h5) exist, try loading weights
        try:
            predictor.model.load_weights('best_model.h5')
            print("✅ Loaded best model weights for evaluation")
        except Exception:
            print("⚠️ Using final training state for evaluation")
            pass

    metrics = predictor.evaluate_model(X_test, y_test, batch_size=args.predict_batch_size)
    
    print("\n" + "=" * 40)
    print("📊 FINAL TEST METRICS")
    print("=" * 40)
    print(f"  MSE: {metrics['mse']:.6f}")
    print(f"  MAE: {metrics['mae']:.6f}")
    print(f"  RMSE: {metrics['rmse']:.6f}")
    
    # Print top IPs by per-IP MAE
    if 'per_ip_mae' in metrics:
        per_ip = metrics['per_ip_mae']
        # sort descending by error
        idxs = np.argsort(per_ip)[::-1]
        top_k = min(10, len(per_ip))
        print(f"\n🔍 Top {top_k} IPs by prediction error (MAE):")
        for i in range(top_k):
            ip = ip_columns[idxs[i]] if idxs[i] < len(ip_columns) else f'ip_{idxs[i]}'
            print(f"  {i+1:2d}. {ip:<15}: MAE={per_ip[idxs[i]]:.6f}")
    print("=" * 40)
    
    # Make sample predictions
    print("\n🔮 Making predictions on test set...")
    sample_predictions = predictor.predict(X_test, batch_size=args.predict_batch_size)
    print(f"Prediction shape (full test set): {sample_predictions.shape}")

    # Generate plots
    print("\n📈 Generating analysis plots...")
    
    print("  → All IPs predictions vs actual...")
    plot_all_ips_predictions(predictor.model, predictor.scaler, X_test, y_test, ip_columns, 
                            y_time_bins=y_time_bins, n_points=300)
    
    print("  → Total traffic by time bin...")
    plot_total_traffic_by_time(predictor.model, predictor.scaler, X_test, y_test, y_time_bins, n_points=300)
    
    print("\n✅ Training and analysis complete!")
    print("📁 Generated files:")
    print("  - best_model.keras (saved model)")
    print("  - all_ips_predictions.png") 
    print("  - total_traffic_by_time.png")

if __name__ == "__main__":
    main()