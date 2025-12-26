import numpy as np
import time
from normalize import OneEuroFilter

def test_filter():
    print("Testing One Euro Filter...")
    f = OneEuroFilter(min_cutoff=1.0, beta=0.01)
    
    # Simulate a steady position with noise
    base_pos = np.array([0.5, 0.5])
    noisy_positions = [base_pos + np.random.normal(0, 0.01, 2) for _ in range(10)]
    
    print("Steady input (with noise) -> Filtered output:")
    for p in noisy_positions:
        out = f(p, dt=0.033)
        print(f"In: {p[0]:.4f} -> Out: {out[0]:.4f} (Diff: {abs(p[0]-out[0]):.4f})")

    # Simulate a fast movement
    print("\nFast movement -> Filtered output:")
    for i in range(5):
        p = base_pos + np.array([i * 0.1, 0])
        out = f(p, dt=0.033)
        print(f"In: {p[0]:.4f} -> Out: {out[0]:.4f} (Diff: {abs(p[0]-out[0]):.4f})")

if __name__ == "__main__":
    test_filter()
