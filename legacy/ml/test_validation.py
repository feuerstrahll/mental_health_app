"""
Test script for input validation - standalone version
"""

import numpy as np

# Load constants from config
LOOKBACK_DAYS = 14
NUM_FEATURES = 4
NUM_CLASSES = 6

def validate_input_shape(X, y=None, lookback_days=None, num_features=None):
    """
    Validates input tensor shape and feature ranges.
    
    Args:
        X: Input features array of shape (batch_size, lookback_days, num_features)
        y: Optional labels array of shape (batch_size, num_classes)
    
    Returns:
        dict: Validation result with status and details
    """
    global LOOKBACK_DAYS, NUM_FEATURES, NUM_CLASSES
    
    if lookback_days is None:
        lookback_days = LOOKBACK_DAYS
    if num_features is None:
        num_features = NUM_FEATURES
    
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'shape': X.shape,
        'dtype': str(X.dtype)
    }
    
    # Check array type
    if not isinstance(X, np.ndarray):
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"X must be numpy.ndarray, got {type(X)}"
        )
        return validation_result
    
    # Check number of dimensions
    if len(X.shape) != 3:
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"X must be 3D (batch_size, {lookback_days}, {num_features}), "
            f"got shape {X.shape}"
        )
        return validation_result
    
    # Check lookback_days
    if X.shape[1] != lookback_days:
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"Expected {lookback_days} lookback days, got {X.shape[1]}. "
            f"Shape is {X.shape}, expected (batch_size, {lookback_days}, {num_features})"
        )
    
    # Check num_features
    if X.shape[2] != num_features:
        validation_result['valid'] = False
        validation_result['errors'].append(
            f"Expected {num_features} features, got {X.shape[2]}. "
            f"Shape is {X.shape}, expected (batch_size, {lookback_days}, {num_features})"
        )
    
    # Check feature value ranges [0, 1]
    if np.any(X < 0.0) or np.any(X > 1.0):
        min_val = np.min(X)
        max_val = np.max(X)
        validation_result['warnings'].append(
            f"Feature values out of [0, 1] range: min={min_val:.4f}, max={max_val:.4f}. "
            f"Consider normalizing data."
        )
    
    # Check NaN or Inf
    if np.any(np.isnan(X)) or np.any(np.isinf(X)):
        validation_result['valid'] = False
        validation_result['errors'].append(
            "Input contains NaN or Inf values"
        )
    
    # Validate labels if provided
    if y is not None:
        if not isinstance(y, np.ndarray):
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"y must be numpy.ndarray, got {type(y)}"
            )
        elif len(y.shape) != 2:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"y must be 2D (batch_size, num_classes), got shape {y.shape}"
            )
        elif y.shape[0] != X.shape[0]:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"X and y batch sizes don't match: X={X.shape[0]}, y={y.shape[0]}"
            )
        elif y.shape[1] != NUM_CLASSES:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"y has {y.shape[1]} classes, expected {NUM_CLASSES}"
            )
        
        # Check that labels are one-hot encoded
        row_sums = np.sum(y, axis=1)
        if not np.allclose(row_sums, 1.0):
            validation_result['warnings'].append(
                "Labels don't appear to be one-hot encoded (row sums != 1.0)"
            )
    
    return validation_result


def print_validation_result(result):
    """Pretty-print validation result."""
    if result['valid']:
        print("✓ Input validation PASSED")
    else:
        print("✗ Input validation FAILED:")
        for error in result['errors']:
            print(f"  ERROR: {error}")
    
    if result['warnings']:
        for warning in result['warnings']:
            print(f"  WARNING: {warning}")
    
    print(f"  Shape: {result['shape']}, dtype: {result['dtype']}")


# Test cases
print("="*60)
print("INPUT VALIDATION TESTS")
print("="*60)

# Test 1: Valid input
print("\nTest 1: Valid input shape (10, 14, 4)")
valid_X = np.random.rand(10, 14, 4).astype(np.float32)
valid_y = np.eye(6)[np.random.randint(0, 6, 10)]
result = validate_input_shape(valid_X, valid_y)
print_validation_result(result)

# Test 2: Invalid lookback_days
print("\nTest 2: Invalid lookback_days (10, 7, 4 - should be 14)")
invalid_X = np.random.rand(10, 7, 4).astype(np.float32)
result = validate_input_shape(invalid_X)
print_validation_result(result)

# Test 3: Invalid num_features
print("\nTest 3: Invalid num_features (10, 14, 3 - should be 4)")
invalid_X = np.random.rand(10, 14, 3).astype(np.float32)
result = validate_input_shape(invalid_X)
print_validation_result(result)

# Test 4: Invalid labels shape
print("\nTest 4: Invalid labels - wrong number of classes (5 instead of 6)")
valid_X = np.random.rand(10, 14, 4).astype(np.float32)
invalid_y = np.eye(5)[np.random.randint(0, 5, 10)]
result = validate_input_shape(valid_X, invalid_y)
print_validation_result(result)

# Test 5: Out of range values
print("\nTest 5: Features out of [0, 1] range")
bad_X = np.random.uniform(-0.5, 1.5, (10, 14, 4)).astype(np.float32)
result = validate_input_shape(bad_X)
print_validation_result(result)

print("\n" + "="*60)
print("✓ All validation tests completed successfully!")
print("="*60)
