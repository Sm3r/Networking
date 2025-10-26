"""
Plotting utilities for network traffic prediction visualization.
"""
import numpy as np
import matplotlib.pyplot as plt


def plot_all_ips_predictions(model, scaler, X_test, y_test, ip_columns, 
                           y_time_bins=None, n_points=200, save_path='all_ips_predictions.png',
                           precomputed_predictions=None):
    """
    Plot predicted vs actual traffic for all IPs in a grid layout.

    Args:
        model: Trained model
        scaler: Fitted scaler for inverse transformation
        X_test, y_test: Test arrays 
        ip_columns: List of IP column names
        y_time_bins: Optional array of time bins
        n_points: Max number of points to plot
        save_path: Path to save the plot
        precomputed_predictions: Optional pre-computed predictions
    """
    # Use precomputed predictions if available, otherwise compute them
    if precomputed_predictions is not None:
        preds_inv = precomputed_predictions
        y_inv = scaler.inverse_transform(y_test)
    else:
        preds = model.predict(X_test)
        preds_inv = scaler.inverse_transform(preds)
        y_inv = scaler.inverse_transform(y_test)

    # Limit to n_points
    n = min(len(y_inv), n_points)
    n_ips = len(ip_columns)

    # Calculate grid dimensions
    n_cols = int(np.ceil(np.sqrt(n_ips)))
    n_rows = int(np.ceil(n_ips / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4*n_cols, 3*n_rows))
    
    # Handle single row/column cases
    if n_rows == 1 and n_cols == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)
    elif n_cols == 1:
        axes = axes.reshape(-1, 1)

    # Plot each IP
    for i, ip_name in enumerate(ip_columns):
        row = i // n_cols
        col = i % n_cols
        ax = axes[row, col]
        
        ax.plot(range(n), y_inv[:n, i], label='Actual', linewidth=1.5, alpha=0.8)
        ax.plot(range(n), preds_inv[:n, i], label='Predicted', linewidth=1.5, alpha=0.8)
        ax.set_title(f'{ip_name}', fontsize=10)
        ax.set_ylabel('Traffic Size', fontsize=8)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # Hide unused subplots
    for i in range(n_ips, n_rows * n_cols):
        row = i // n_cols
        col = i % n_cols
        axes[row, col].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"📊 Plot saved to: {save_path}")
    plt.show()
    plt.close()


def plot_total_traffic_by_time(model, scaler, X_test, y_test, y_time_bins, n_points=200, 
                             save_path='total_traffic_by_time.png', precomputed_predictions=None):
    """
    Plot total predicted vs actual traffic for each time bin.
    
    Args:
        model: Trained model
        scaler: Fitted scaler
        X_test, y_test: Test arrays
        y_time_bins: Array of time bins
        n_points: Max number of points to plot
        save_path: Path to save the plot
        precomputed_predictions: Optional pre-computed predictions
    """
    # Use precomputed predictions if available
    if precomputed_predictions is not None:
        preds_inv = precomputed_predictions
        y_inv = scaler.inverse_transform(y_test)
    else:
        preds = model.predict(X_test)
        preds_inv = scaler.inverse_transform(preds)
        y_inv = scaler.inverse_transform(y_test)
    
    # Calculate total traffic per time bin
    total_actual = y_inv.sum(axis=1)
    total_predicted = preds_inv.sum(axis=1)
    
    # Limit to n_points
    n = min(len(total_actual), n_points)
    
    # Use time bins if available
    if y_time_bins is not None and len(y_time_bins) >= n:
        x_axis = y_time_bins[:n]
        x_label = 'Time Bin'
    else:
        x_axis = range(n)
        x_label = 'Sample Index'
    
    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.plot(x_axis, total_actual[:n], label='Actual', linewidth=2, alpha=0.8)
    ax.plot(x_axis, total_predicted[:n], label='Predicted', linewidth=2, alpha=0.8)
    
    ax.set_title('Total Network Traffic: Predicted vs Actual', fontsize=16, weight='bold')
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel('Total Traffic Volume', fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # Add statistics
    mae = np.mean(np.abs(total_actual[:n] - total_predicted[:n]))
    rmse = np.sqrt(np.mean((total_actual[:n] - total_predicted[:n])**2))
    correlation = np.corrcoef(total_actual[:n], total_predicted[:n])[0, 1]
    
    stats_text = f'MAE: {mae:.2f}\nRMSE: {rmse:.2f}\nCorr: {correlation:.3f}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"📊 Plot saved to: {save_path}")
    plt.show()
    plt.close()