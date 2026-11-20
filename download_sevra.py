from datasets import load_dataset

# Download malicious PRs
malicious_ds = load_dataset(
    "RedAI4Code/SEVRA",
    "cwe79-deterministic"
)

# Download benign PRs
benign_ds = load_dataset(
    "RedAI4Code/SEVRA",
    "cwe79-benign"
)

# Save datasets locally
malicious_ds.save_to_disk("ml/data/raw/sevra_malicious")
benign_ds.save_to_disk("ml/data/raw/sevra_benign")

print("Both datasets downloaded successfully!")