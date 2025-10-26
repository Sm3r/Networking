import pandas as pd

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
        
        return data
        
    except FileNotFoundError:
        print(f"Error: File not found at {csv_file_path}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def bin_timestamps_and_aggregate_traffic(data: pd.DataFrame, bin_size: float = 2.0) -> pd.DataFrame:
    data['time_bin'] = (data['virtual_timestamp'] // bin_size) * bin_size
    
    # Create separate dataframes for source and destination traffic
    src_traffic = data[['time_bin', 'src_ip', 'length']].copy()
    src_traffic.rename(columns={'src_ip': 'ip'}, inplace=True)
    
    dst_traffic = data[['time_bin', 'dst_ip', 'length']].copy()
    dst_traffic.rename(columns={'dst_ip': 'ip'}, inplace=True)
    
    # Combine source and destination traffic
    all_traffic = pd.concat([src_traffic, dst_traffic], ignore_index=True)
    
    # Group by time_bin and ip, then sum the traffic length
    aggregated = all_traffic.groupby(['time_bin', 'ip'])['length'].sum().reset_index()
    aggregated.rename(columns={'length': 'total_traffic_size'}, inplace=True)
    
    # Sort by time_bin and then by ip for better readability
    aggregated = aggregated.sort_values(['time_bin', 'ip']).reset_index(drop=True)
    
    return aggregated