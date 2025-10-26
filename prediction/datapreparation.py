import pandas as pd
import numpy as np

def load_and_prepare_data(csv_file_path: str) -> pd.DataFrame:
    try:
        # Load the dataset
        data = pd.read_csv(csv_file_path)
        
        # Remove column real_timestamp if it exists
        if 'real_timestamp' in data.columns:
            data = data.drop(columns=['real_timestamp'])
        
        # Convert data types properly
        if 'src_ip' in data.columns:
            data['src_ip'] = data['src_ip'].astype(str).replace('nan', 'N/A')
        if 'dst_ip' in data.columns:
            data['dst_ip'] = data['dst_ip'].astype(str).replace('nan', 'N/A')
        if 'src_port' in data.columns:
            data['src_port'] = data['src_port'].astype(str).replace('nan', 'N/A')
        if 'dst_port' in data.columns:
            data['dst_port'] = data['dst_port'].astype(str).replace('nan', 'N/A')
        
        # Remove rows where src_ip or dst_ip is 'N/A'
        data = data[(data['src_ip'] != 'N/A') & (data['dst_ip'] != 'N/A')]
        
        # Filter out localhost traffic (127.0.0.1) as it's noise
        data = data[(data['src_ip'] != '127.0.0.1') & (data['dst_ip'] != '127.0.0.1')]
        
        return data
        
    except FileNotFoundError:
        print(f"Error: File not found at {csv_file_path}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def bin_timestamps_and_aggregate_traffic(data: pd.DataFrame, bin_size: float = 2.0, min_traffic_threshold: int = 1000) -> pd.DataFrame:
    """
    Bin timestamps and aggregate traffic with improved filtering.
    
    Args:
        data: Raw packet data
        bin_size: Time bin size in seconds
        min_traffic_threshold: Minimum total traffic per IP to include (filters out sparse IPs)
    
    Returns:
        Aggregated traffic dataframe
    """
    data['time_bin'] = (data['virtual_timestamp'] // bin_size) * bin_size
    
    # Create separate dataframes for source and destination traffic
    src_traffic = data[['time_bin', 'src_ip', 'length']].copy()
    src_traffic.rename(columns={'src_ip': 'ip'}, inplace=True)
    
    dst_traffic = data[['time_bin', 'dst_ip', 'length']].copy()
    dst_traffic.rename(columns={'dst_ip': 'ip'}, inplace=True)
    
    # Combine source and destination traffic
    all_traffic = pd.concat([src_traffic, dst_traffic], ignore_index=True)
    
    # Filter out IPs with very low total traffic (noise)
    ip_total_traffic = all_traffic.groupby('ip')['length'].sum()
    valid_ips = ip_total_traffic[ip_total_traffic >= min_traffic_threshold].index
    all_traffic = all_traffic[all_traffic['ip'].isin(valid_ips)]
    
    # Group by time_bin and ip, then sum the traffic length
    aggregated = all_traffic.groupby(['time_bin', 'ip'])['length'].sum().reset_index()
    aggregated.rename(columns={'length': 'total_traffic_size'}, inplace=True)
    
    # Sort by time_bin and then by ip for better readability
    aggregated = aggregated.sort_values(['time_bin', 'ip']).reset_index(drop=True)
    
    return aggregated

def add_temporal_features(aggregated_data: pd.DataFrame, bin_size: float = 2.0) -> pd.DataFrame:
    """
    Add temporal features to help the model learn time patterns.
    
    Args:
        aggregated_data: Aggregated traffic data
        bin_size: Time bin size in seconds
        
    Returns:
        Data with additional temporal features
    """
    df = aggregated_data.copy()
    
    # Normalize time to [0, 1] within the total duration
    max_time = df['time_bin'].max()
    df['time_normalized'] = df['time_bin'] / max_time if max_time > 0 else 0
    
    # Cyclic time encoding (useful if there are repeating patterns)
    # Assuming a "day" could be represented in the simulation
    period = 100.0  # Adjust based on simulation characteristics
    df['time_sin'] = np.sin(2 * np.pi * df['time_bin'] / period)
    df['time_cos'] = np.cos(2 * np.pi * df['time_bin'] / period)
    
    # Time of day feature (scaled to hours if applicable)
    df['time_hour'] = (df['time_bin'] % 86400) / 3600 if bin_size < 3600 else 0
    
    return df

def prepare_sequences_with_time(aggregated_data: pd.DataFrame, sequence_length: int = 12, 
                                include_time_features: bool = True) -> tuple:
    """
    Prepare sequences with optional time features for improved predictions.
    
    Args:
        aggregated_data: Aggregated traffic data
        sequence_length: Number of time steps to look back
        include_time_features: Whether to include temporal features
        
    Returns:
        tuple: (X, y, feature_columns, y_time_bins)
    """
    from sklearn.preprocessing import MinMaxScaler
    
    # Add temporal features if requested
    if include_time_features:
        aggregated_data = add_temporal_features(aggregated_data)
    
    # Ensure data is sorted by time
    aggregated_data = aggregated_data.sort_values('time_bin').reset_index(drop=True)
    
    # Get unique IPs
    unique_ips = sorted([ip for ip in aggregated_data['ip'].unique() if ip != '127.0.0.1'])
    
    # Create pivot table for traffic
    pivot_traffic = aggregated_data.pivot(
        index='time_bin', 
        columns='ip', 
        values='total_traffic_size'
    ).fillna(0)
    
    # Ensure all IPs are present
    for ip in unique_ips:
        if ip not in pivot_traffic.columns:
            pivot_traffic[ip] = 0
    
    # Sort columns by IP for consistency
    pivot_traffic = pivot_traffic[sorted(pivot_traffic.columns)]
    
    # Scale the traffic data
    scaler = MinMaxScaler()
    scaled_traffic = scaler.fit_transform(pivot_traffic.values)
    
    # If including time features, add them
    if include_time_features:
        # Get time features for each time bin
        time_features_df = aggregated_data[['time_bin', 'time_normalized', 'time_sin', 'time_cos']].drop_duplicates('time_bin').sort_values('time_bin')
        time_features_df = time_features_df.set_index('time_bin')
        time_features_df = time_features_df.reindex(pivot_traffic.index, fill_value=0)
        
        # Scale time features
        time_scaler = MinMaxScaler()
        scaled_time = time_scaler.fit_transform(time_features_df.values)
        
        # Combine traffic and time features
        combined_features = np.concatenate([scaled_traffic, scaled_time], axis=1)
    else:
        combined_features = scaled_traffic
    
    # Create sequences
    X, y = [], []
    for i in range(sequence_length, len(scaled_traffic)):
        X.append(combined_features[i-sequence_length:i])
        y.append(scaled_traffic[i])  # Predict only traffic, not time features
    
    y_time_bins = pivot_traffic.index.values[sequence_length:]
    
    return np.array(X), np.array(y), pivot_traffic.columns.tolist(), y_time_bins, scaler