import torch
import torch.nn as nn

class LSTM(nn.Module):

    def __init__(self, input_size=1, hidden_size=50, output_size=1, num_layers=1, dropout=0.2):

        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = nn.Dropout(dropout)
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_size, output_size)

    def forward(self, x):

        lstm_out, (hn, cn) = self.lstm(x)
        last_time_step_out = lstm_out[:, -1, :]

        output = self.dropout(last_time_step_out)
        predictions = self.linear(output)
        return predictions
