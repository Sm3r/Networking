import pyshark
import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("display.width", None)

def get_data(path):
    cap = pyshark.FileCapture(path)
        
    rows = []
    first_pkt_time = None

    for pkt in cap:
        if first_pkt_time is None:
            first_pkt_time = pkt.sniff_time
        row = {"time": (pkt.sniff_time - first_pkt_time).total_seconds()}
        for layer in pkt.layers:
            layer_name = layer.layer_name
            for field_name in layer.field_names:
                try:
                    value = getattr(layer, field_name)
                except AttributeError:
                    value = None
                row[f"{layer_name}.{field_name}"] = value
        rows.append(row)

    df = pd.DataFrame(rows)
    cap.close()
    return df

def cleanse_data(df):
    # At least 50% non-null required
    threshold = len(df) * 0.5  
    df_cleaned = df.dropna(axis=1, thresh=threshold)
    print(f"Original shape: {df.shape}")

    drop_cols = [
        # Ethernet addresses and metadata
        "eth.dst", "eth.dst_resolved", "eth.dst_oui", "eth.dst_lg", "eth.dst_ig",
        "eth.addr", "eth.addr_resolved", "eth.addr_oui", "eth.lg", "eth.ig",
        "eth.src", "eth.src_resolved", "eth.src_oui", "eth.src_lg", "eth.src_ig",
        "eth.type", "eth.stream",

        # IP identifiers / redundant addresses
        "ip.id", "ip.checksum", "ip.checksum_status", "ip.stream",
        "ip.addr", "ip.src_host", "ip.host", "ip.dst_host",

        # UDP identifiers / checksum / payload
        "udp.checksum", "udp.checksum_status", "udp.stream", "udp.stream_pnum",
        "udp.", "udp.payload"
    ]
    df = df_cleaned.drop(columns=[c for c in drop_cols if c in df_cleaned.columns])

    df['packet_len'] = df['ip.len'].astype(float)
    df = df.dropna(subset=['ip.src', 'ip.dst', 'ip.len'])


    time_window = 1  # seconds

    # Assign each packet to a time bin
    df['time_bin'] = (df['time'] // time_window) * time_window

    # Outgoing traffic
    out_traffic = df.groupby(['ip.src', 'time_bin']).agg(
        out_throughput=('packet_len', 'sum'),
        out_count=('packet_len', 'count')
    ).reset_index().rename(columns={'ip.src': 'node'})

    # Incoming traffic
    in_traffic = df.groupby(['ip.dst', 'time_bin']).agg(
        in_throughput=('packet_len', 'sum'),
        in_count=('packet_len', 'count')
    ).reset_index().rename(columns={'ip.dst': 'node'})

    # Merge incoming + outgoing traffic per node per time_bin
    traffic_per_node_total = pd.merge(out_traffic, in_traffic, on=['node', 'time_bin'], how='outer').fillna(0)

    # Total traffic
    traffic_per_node_total['total_throughput'] = traffic_per_node_total['out_throughput'] + traffic_per_node_total['in_throughput']
    traffic_per_node_total['total_count'] = traffic_per_node_total['out_count'] + traffic_per_node_total['in_count']

    print(f"Cleaned: {traffic_per_node_total}")
    return traffic_per_node_total

def fill_reindexing(df, time_window=1):
    # Get all unique nodes
    all_nodes = df['node'].unique()
    
    # Create complete time range from 0 to max time (including gaps with no traffic)
    max_time = int(df['time_bin'].max())
    # Start from 0 to include all possible time bins, even those with no traffic
    all_time_bins = np.arange(0, max_time + time_window, time_window)
    
    # Create a complete index with all combinations of nodes and time_bins
    complete_index = pd.MultiIndex.from_product([all_nodes, all_time_bins], names=['node', 'time_bin'])
    complete_df = pd.DataFrame(index=complete_index).reset_index()
    
    # Merge with original data to fill in missing node-time combinations with 0
    df_filled = pd.merge(complete_df, df, on=['node', 'time_bin'], how='left').fillna(0)
    
    print(f"Reindexed: {df_filled}")
    return df_filled

def scale_data(df):
    scaler = StandardScaler()
    feature_cols = [col for col in df.columns if col not in ['node', 'time_bin']]
    df[feature_cols] = scaler.fit_transform(df[feature_cols])
    
    print(f"Scaled: {df}")
    return df