from pathlib import Path
import torch
from torch.utils.data import DataLoader

try:
    from train.preprocessing import prepare_network_data
    from train.data_loader import NetworkDataset
    from train.network import LSTM
except ImportError:
    from preprocessing import prepare_network_data
    from data_loader import NetworkDataset
    from network import LSTM

DATA_DIR = Path(__file__).parent.parent / "data"

def train(model, dataloader, criterion, optimizer):
    model.train()
    running_loss = 0.0

    for batch_x, batch_y in dataloader:
        optimizer.zero_grad()
        predictions = model(batch_x)
        loss = criterion(predictions, batch_y)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * batch_x.size(0)

    epoch_loss = running_loss / len(dataloader.dataset)
    return epoch_loss

def evaluate(model, dataloader, criterion):
    model.eval()
    running_loss = 0.0

    with torch.no_grad():
        for batch_x, batch_y in dataloader:
            predictions = model(batch_x)
            loss = criterion(predictions, batch_y)

            running_loss += loss.item() * batch_x.size(0)

    epoch_loss = running_loss / len(dataloader.dataset)
    return epoch_loss

def main():
    ### Hyperparameters
    BATCH_SIZE = 64
    NUM_EPOCHS = 60
    LEARNING_RATE = 1e-3

    prepare_network_data(data_dir=DATA_DIR, force_rebuild=False)

    train_dataset = NetworkDataset(data_dir=DATA_DIR, training=True)
    test_dataset = NetworkDataset(data_dir=DATA_DIR, training=False)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    model = LSTM()
    criterion = torch.nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode='min',
        factor=0.5,
        patience=5
    )

    print("Starting training loop...")
    for epoch in range(NUM_EPOCHS):

        train_loss = train(model, train_loader, criterion, optimizer)
        val_loss = evaluate(model, test_loader, criterion)
        scheduler.step(val_loss)

        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch [{epoch+1}/{NUM_EPOCHS}] | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f} | LR: {current_lr:.6f}")

    torch.save(model.state_dict(), "model_LSTM.pth")
    print("Training complete. Model saved to 'model_LSTM.pth'")

if __name__ == "__main__":
    main()
