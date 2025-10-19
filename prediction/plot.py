import numpy as np
import matplotlib.pyplot as plt

def plot_all_ips_predictions(model, scaler, X_test, y_test, ip_columns, 
                           y_time_bins=None, n_points=200, save_path='all_ips_predictions.png'):
    """
    Plot predicted vs actual for all IPs in a grid layout.

    Args:
        model: Trained model
        scaler: Fitted scaler for inverse transformation
        X_test, y_test: test arrays 
        ip_columns: list of IP column names (order matches model output)
        y_time_bins: optional array of time bins corresponding to y_test
        n_points: max number of points to plot
        save_path: Path to save the plot
    """
    # Make predictions and inverse-transform
    preds = model.predict(X_test)
    preds_inv = scaler.inverse_transform(preds)
    y_inv = scaler.inverse_transform(y_test)

    # Clip to n_points
    n = min(len(y_inv), n_points)
    n_ips = len(ip_columns)

    # Calculate grid size - aim for roughly square layout
    n_cols = int(np.ceil(np.sqrt(n_ips)))
    n_rows = int(np.ceil(n_ips / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4*n_cols, 3*n_rows))
    
    # Handle case where we only have one row or column
    if n_rows == 1:
        axes = axes.reshape(1, -1)
    elif n_cols == 1:
        axes = axes.reshape(-1, 1)

    # Plot each IP
    for i, ip_name in enumerate(ip_columns):
        row = i // n_cols
        col = i % n_cols
        ax = axes[row, col]
        
        ax.plot(range(n), y_inv[:n, i], label='Actual', linewidth=1.5)
        ax.plot(range(n), preds_inv[:n, i], label='Predicted', alpha=0.8, linewidth=1.5)
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
    plt.show()

def plot_total_traffic_by_time(model, scaler, X_test, y_test, y_time_bins, n_points=200, save_path='total_traffic_by_time.png'):
    """
    Plot total predicted vs actual traffic for each time bin.
    
    Args:
        model: Trained model
        scaler: Fitted scaler for inverse transformation
        X_test, y_test: test arrays
        y_time_bins: array of time bins corresponding to y_test
        n_points: max number of points to plot
        save_path: Path to save the plot
    """
    # Make predictions and inverse-transform
    preds = model.predict(X_test)
    preds_inv = scaler.inverse_transform(preds)
    y_inv = scaler.inverse_transform(y_test)
    
    # Calculate total traffic per time bin (sum across all IPs)
    total_actual = y_inv.sum(axis=1)
    total_predicted = preds_inv.sum(axis=1)
    
    # Clip to n_points
    n = min(len(total_actual), n_points)
    
    # Use time bins if available, otherwise use sample indices
    if y_time_bins is not None and len(y_time_bins) >= n:
        x_axis = y_time_bins[:n]
        x_label = 'Time Bin'
    else:
        x_axis = range(n)
        x_label = 'Test Sample Index'
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.plot(x_axis, total_actual[:n], label='Actual Total Traffic', linewidth=2, alpha=0.8)
    ax.plot(x_axis, total_predicted[:n], label='Predicted Total Traffic', linewidth=2, alpha=0.8)
    
    ax.set_title('Total Network Traffic: Predicted vs Actual by Time', fontsize=16, weight='bold')
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel('Total Traffic Volume', fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # Add some statistics as text
    mae = np.mean(np.abs(total_actual[:n] - total_predicted[:n]))
    rmse = np.sqrt(np.mean((total_actual[:n] - total_predicted[:n])**2))
    correlation = np.corrcoef(total_actual[:n], total_predicted[:n])[0, 1]
    
    stats_text = f'MAE: {mae:.4f}\nRMSE: {rmse:.4f}\nCorrelation: {correlation:.4f}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()