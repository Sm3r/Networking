from prediction.data_processing import get_data, cleanse_data, fill_reindexing, scale_data

# ---------------------------
# CONFIG / HYPERPARAMETERS
# ---------------------------
SEQ_LEN = 20
HORIZON = 1
BATCH_SIZE = 64
EPOCHS = 50
HIDDEN_SIZE = 128
NUM_LAYERS = 2


df = get_data("prediction/dump.pcap")
df = cleanse_data(df)
df = fill_reindexing(df)
df = scale_data(df)

### TODO

