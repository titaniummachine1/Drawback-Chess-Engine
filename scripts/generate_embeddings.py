"""
Generate MiniLM Embeddings for Drawback Descriptions

This script converts natural language drawback descriptions into 384-dimensional 
vectors that the neural network can understand.
"""

import json
import numpy as np
import os
from pathlib import Path

# Try to import sentence_transformers, offer instructions if missing
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: 'sentence-transformers' not found.")
    print("Please run: pip install sentence-transformers")
    exit(1)


def generate_drawback_embeddings(json_file: str, output_file: str):
    """
    Reads a JSON file of drawbacks and generates embeddings.
    
    Expected JSON format:
    {
        "drawbacks": [
            {"name": "Vegan", "description": "Cannot capture pieces with pawns"},
            ...
        ]
    }
    """
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found.")
        return

    with open(json_file, 'r') as f:
        data = json.load(f)
    
    drawbacks = data.get("drawbacks", [])
    if not drawbacks:
        print("No drawbacks found in JSON.")
        return

    # Initialize the lightweight "Toaster-friendly" model
    print("Loading all-MiniLM-L6-v2 (22MB)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Combine name and description for better context
    sentences = [
        f"{d['name']}: {d['description']}" for d in drawbacks
    ]
    
    print(f"Encoding {len(sentences)} drawbacks...")
    embeddings = model.encode(sentences)
    
    # Save as numpy matrix and map
    np.save(output_file, embeddings)
    
    # Save a mapping for lookup
    mapping = {d['name']: i for i, d in enumerate(drawbacks)}
    with open(Path(output_file).with_suffix('.json'), 'w') as f:
        json.dump(mapping, f, indent=2)
        
    print(f"Success! Saved embeddings to {output_file}")


if __name__ == "__main__":
    # Example usage
    os.makedirs("data/embeddings", exist_ok=True)
    
    # Create a dummy JSON if none exists for demo
    dummy_path = "data/drawbacks_list.json"
    if not os.path.exists(dummy_path):
        dummy_data = {
            "drawbacks": [
                {"name": "Vegan", "description": "Cannot capture pieces with pawns."},
                {"name": "Knight Immobility", "description": "Knights cannot move or capture."},
                {"name": "No Castling", "description": "You are not allowed to castle."},
                {"name": "Diagonal Dash", "description": "Bishops and Queens can only move forward."}
            ]
        }
        with open(dummy_path, 'w') as f:
            json.dump(dummy_data, f, indent=2)
            
    generate_drawback_embeddings(dummy_path, "data/embeddings/drawback_vectors.npy")
