## Problem: Time-series forecasting of throughput per network node.

# Network Traffic Forecasting Pipeline (RNN)

This pipeline prepares network packet data for per-node traffic prediction using an RNN (LSTM/GRU). It converts raw packet logs into per-node time series, constructs features, sequences, and trains a temporal model.

---

## Step-by-Step Overview

1. **Decide Target & Horizon**  
   - Define what to predict (e.g., total bytes per node) and prediction horizon.  
   - Choose resample interval (1s, 1min, etc.) based on use case.

2. **Parse & Clean Data**  
   - Convert timestamps to datetime, sort, remove duplicates, handle corrupt rows.  
   - Ensures temporal consistency and data integrity.

3. **Expand Packets to Node-Centric Events**  
   - Create two rows per packet: source (outgoing) and destination (incoming).  
   - Needed for per-node aggregation of traffic.

4. **Resample & Aggregate**  
   - Bin data into fixed intervals (e.g., 1min) per node.  
   - Aggregate bytes, packets, protocols, and flags.  
   - Converts irregular event streams into regular time series.

5. **Feature Construction**  
   - Compute per-interval features: `bytes_in/out`, `pkts_in/out`, `avg_pkt_size`, protocol counts, top ports, TCP flags, DNS query counts, rolling statistics.  
   - Helps model capture temporal patterns and node behavior.

6. **Fill Missing Intervals**  
   - Reindex time series per node to include empty bins; fill with zeros or NaN.  
   - Required for consistent sequence lengths for RNN input.

7. **Scale / Transform Features**  
   - Apply `log1p` to skewed features (e.g., bytes) and scale (StandardScaler/MinMaxScaler).  
   - Fit scalers on training data only to avoid data leakage.  

8. **Create Sequences & Labels**  
   - Use sliding windows of `seq_len` intervals to create input sequences.  
   - Associate each sequence with target value at `t + horizon`.  
   - Include node IDs for global models with embeddings.

9. **Train / Validation / Test Split**  
   - Split data by time (earliest → train, later → val, latest → test).  
   - Ensures realistic evaluation without future leakage.

10. **Train RNN Model**  
    - LSTM/GRU with optional node embeddings.  
    - Loss: MSE/MAE; monitor metrics (RMSE, MAE, MAPE).  
    - Compare performance against simple baselines (persistence, moving average).

11. **Deploy & Monitor**  
    - Save model, scalers, node mappings.  
    - Build inference pipeline for per-interval prediction.  
    - Monitor errors, detect feature/traffic drift, retrain periodically.

---

## Notes & Tips
- Use rolling features and protocol/port counts for richer representation.  
- Log-transform skewed traffic to stabilize learning.  
- Sliding window sequences must not cross large gaps without handling missing data.  
- Prefer global RNN with node embeddings if many nodes exist; per-node models work for small networks.  
- Time-ordered splits prevent unrealistic performance estimates.  

---

This pipeline transforms raw packet captures into ready-to-use input for temporal neural networks for per-node traffic forecasting.
