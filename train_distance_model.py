import argparse
from pathlib import Path
from typing import Dict

import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class DistanceRegressor(nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


def prepare_dataset(dataframe: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> Dict[str, object]:
    feature_columns = ["width", "height", "area"]
    X = dataframe[feature_columns].to_numpy(dtype=float)
    y = dataframe["distance"].to_numpy(dtype=float)

    label_encoder = LabelEncoder()
    class_labels = label_encoder.fit_transform(dataframe["object_class"].astype(str))
    X_augmented = torch.cat(
        [
            torch.tensor(X, dtype=torch.float32),
            torch.tensor(class_labels.reshape(-1, 1), dtype=torch.float32),
        ],
        dim=1,
    )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_augmented)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    return {
        "X_train": torch.tensor(X_train, dtype=torch.float32),
        "X_test": torch.tensor(X_test, dtype=torch.float32),
        "y_train": torch.tensor(y_train, dtype=torch.float32).view(-1, 1),
        "y_test": torch.tensor(y_test, dtype=torch.float32).view(-1, 1),
        "feature_columns": feature_columns,
        "scaler": scaler,
        "label_encoder": label_encoder,
    }


def train_model(csv_path: str | Path, model_path: str | Path = "distance_model.pth", epochs: int = 80, batch_size: int = 8) -> None:
    dataframe = pd.read_csv(csv_path)
    prepared = prepare_dataset(dataframe)

    train_dataset = TensorDataset(prepared["X_train"], prepared["y_train"])
    test_dataset = TensorDataset(prepared["X_test"], prepared["y_test"])

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    model = DistanceRegressor(input_dim=prepared["X_train"].shape[1])
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        if epoch % 20 == 0 or epoch == epochs - 1:
            print(f"Epoch {epoch:03d} | loss: {running_loss / max(1, len(train_loader)):.4f}")

    model.eval()
    mae = 0.0
    total = 0.0
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            predictions = model(batch_x)
            mae += torch.abs(predictions - batch_y).sum().item()
            total += batch_y.size(0)

    mae = mae / max(1, total)
    print(f"Test MAE: {mae:.4f} meters")

    torch.save(model.state_dict(), model_path)
    print(f"Saved model to {model_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the distance regression model")
    parser.add_argument("--csv", required=True, help="CSV file produced by the bounding box extractor")
    parser.add_argument("--model-output", default="distance_model.pth", help="File where the trained model will be saved")
    parser.add_argument("--epochs", type=int, default=80, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Mini-batch size")
    args = parser.parse_args()

    train_model(args.csv, args.model_output, epochs=args.epochs, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
