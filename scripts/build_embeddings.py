"""
scripts/build_embeddings.py — Build Offline Embeddings for Closed Cases

Encodes all 5,565 closed cases (both confirmed_fraud and cleared)
using sentence-transformers/all-MiniLM-L6-v2 and saves to disk.
"""

import os
import sys
import json
import time
import pandas as pd
import numpy as np

# Ensure root in path
sys.path.insert(0, ".")
from src.memory.embeddings import embed_texts

PROCESSED_DIR = os.path.join("data", "processed")
CASES_PATH = os.path.join(PROCESSED_DIR, "v_closed_case.csv")
EMBEDDINGS_OUT = os.path.join(PROCESSED_DIR, "case_embeddings.npy")
IDS_OUT = os.path.join(PROCESSED_DIR, "case_ids.json")


def build_embeddings():
    print(f"Loading closed cases from {CASES_PATH}...")
    t0 = time.time()
    df_cases = pd.read_csv(CASES_PATH)
    total_cases = len(df_cases)
    print(f"Loaded {total_cases} cases (cleared: {(df_cases['outcome'] == 'cleared').sum()}).")

    texts = []
    case_ids = []

    for _, row in df_cases.iterrows():
        case_id = str(row["case_id"]).strip()
        pattern = str(row["pattern"]).strip() if pd.notna(row["pattern"]) else "none"
        outcome = str(row["outcome"]).strip() if pd.notna(row["outcome"]) else "unknown"
        notes = str(row["analyst_notes"]).strip() if pd.notna(row["analyst_notes"]) else ""
        
        # Fallback if analyst_notes is empty
        if notes:
            text = f"{pattern} {outcome} {notes}"
        else:
            text = f"{pattern} {outcome}"
            
        texts.append(text)
        case_ids.append(case_id)

    print(f"Encoding {len(texts)} case summaries with all-MiniLM-L6-v2...")
    embeddings = embed_texts(texts, batch_size=128, show_progress_bar=True)
    
    print(f"Saving embeddings to {EMBEDDINGS_OUT} (shape: {embeddings.shape})...")
    np.save(EMBEDDINGS_OUT, embeddings)

    print(f"Saving case IDs to {IDS_OUT}...")
    with open(IDS_OUT, "w", encoding="utf-8") as f:
        json.dump(case_ids, f, indent=2)

    print(f"=== EMBEDDINGS BUILT SUCCESSFULLY IN {time.time() - t0:.2f}s ===")


if __name__ == "__main__":
    build_embeddings()
