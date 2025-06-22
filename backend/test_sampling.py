#!/usr/bin/env python3
"""
Test script for dataset sampling functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from jobs import apply_dataset_sampling
import json

def test_sampling():
    """Test the dataset sampling functionality"""
    
    # Test data path
    dataset_path = "datasets/mohler_dataset.csv"
    
    print("🧪 Testing Dataset Sampling Functionality")
    print("=" * 50)
    
    # Test 1: All rows
    print("\n1. Testing 'all' sampling type:")
    config_all = {"sampling_type": "all"}
    df_all = apply_dataset_sampling(dataset_path, config_all)
    print(f"   Result: {len(df_all)} rows")
    
    # Test 2: Random sampling
    print("\n2. Testing 'random' sampling type:")
    config_random = {"sampling_type": "random", "sampling_size": 100}
    df_random = apply_dataset_sampling(dataset_path, config_random)
    print(f"   Result: {len(df_random)} rows (requested 100)")
    
    # Test 3: Range sampling
    print("\n3. Testing 'range' sampling type:")
    config_range = {"sampling_type": "range", "sampling_start_row": 1, "sampling_end_row": 50}
    df_range = apply_dataset_sampling(dataset_path, config_range)
    print(f"   Result: {len(df_range)} rows (requested rows 1-50)")
    
    # Test 4: Preview first few rows of each
    print("\n4. Preview of sampled data:")
    print(f"   All data columns: {list(df_all.columns)}")
    print(f"   Random sample first row: {df_random.iloc[0].to_dict()}")
    print(f"   Range sample first row: {df_range.iloc[0].to_dict()}")
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_sampling()
