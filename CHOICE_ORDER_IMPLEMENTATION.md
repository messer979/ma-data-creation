# choiceOrder Function Implementation Summary

## Overview
Added a new `choiceOrder` function to the template functions module that provides sequential selection of values from a list, similar to `choiceUnique` but with deterministic ordering instead of random selection.

## Feature Comparison

| Feature | choice() | choiceUnique() | choiceOrder() |
|---------|----------|----------------|---------------|
| Selection Method | Random | Random (non-repeating) | Sequential (first to last) |
| Resets When | N/A (always random) | After all options used | After all options used |
| Use Case | Random variety | No duplicates until exhausted | Predictable pattern |

## Implementation Details

### Files Modified
1. **data_creation/template_functions.py**
   - Added `choiceOrder` support to `generate_random_value()` function (fallback behavior)
   - Added `choiceOrder` support to `generate_random_value_with_context()` function (main implementation)
   - Updated `apply_random_fields_with_arrays()` to handle both choiceUnique and choiceOrder fields
   - Updated docstrings to document the new functionality

2. **gen_template_spec.json**
   - Added documentation for `choiceOrder` field type
   - Enhanced documentation for `choiceUnique` to clarify reset behavior

### How It Works
- **Context Tracking**: Uses a shared `unique_context` dictionary to track the current index position for each field path
- **Sequential Selection**: On each call, selects the value at current index position, then increments for next call
- **Wraparound**: When reaching the end of the list, automatically wraps around to the beginning (using modulo operator)
- **Isolation**: Each field path maintains its own independent counter, prefixed with `"choiceOrder:"` to avoid conflicts with `choiceUnique`

### Example Usage

#### Generation Template
```json
{
  "RandomFields": [
    {
      "FieldName": "Items.Size",
      "FieldType": "choiceOrder(SMALL,MEDIUM,LARGE,XLARGE)"
    },
    {
      "FieldName": "Priority",
      "FieldType": "choiceOrder(LOW,NORMAL,HIGH)"
    }
  ]
}
```

#### Expected Output
For a template generating 10 items:
- Item 1: Size=SMALL, Priority=LOW
- Item 2: Size=MEDIUM, Priority=NORMAL
- Item 3: Size=LARGE, Priority=HIGH
- Item 4: Size=XLARGE, Priority=LOW
- Item 5: Size=SMALL, Priority=NORMAL
- Item 6: Size=MEDIUM, Priority=HIGH
- Item 7: Size=LARGE, Priority=LOW
- Item 8: Size=XLARGE, Priority=NORMAL
- Item 9: Size=SMALL, Priority=HIGH
- Item 10: Size=MEDIUM, Priority=LOW

## Testing

### Test Script
Created `test_choice_order.py` which validates:
1. ✅ Basic choiceOrder without context (fallback behavior)
2. ✅ Sequential selection with proper wraparound
3. ✅ Independent counters for different field paths
4. ✅ Comparison with choiceUnique behavior

### Test Results
All tests passed successfully. The function correctly:
- Maintains sequential ordering
- Wraps around when list is exhausted
- Maintains separate state for different fields
- Works in both array and non-array contexts

## Use Cases

### When to Use choiceOrder
- **Predictable Patterns**: When you need data to follow a specific repeating pattern
- **Round-Robin Assignment**: Distributing values evenly across records
- **Testing Sequences**: Creating deterministic test data for validation
- **Ordered Categories**: Cycling through priority levels, statuses, or types in order

### When to Use choiceUnique
- **Avoiding Duplicates**: When values should not repeat until all options are used
- **Random Distribution**: When you want variety but with eventual exhaustion
- **Unique Identifiers**: For codes or IDs that need to be unique within a batch

### When to Use choice
- **Pure Randomness**: When order and uniqueness don't matter
- **High Repetition OK**: When it's fine for values to repeat immediately
- **Large Option Sets**: When the option pool is large and repetition is acceptable

## Technical Notes

### Context Key Format
- choiceUnique: `"{array_path}.{field_path}"` or `"{field_path}"`
- choiceOrder: `"choiceOrder:{array_path}.{field_path}"` or `"choiceOrder:{field_path}"`

This prefixing ensures that choiceUnique and choiceOrder can operate on the same field without interfering with each other.

### Storage Format
- **choiceUnique**: Stores a set of used values
- **choiceOrder**: Stores an integer index

Both use the same `unique_context` dictionary parameter but store different data types based on the prefix.

## Backward Compatibility

✅ All changes are backward compatible:
- Existing templates using `choice()` and `choiceUnique()` continue to work unchanged
- The `unique_context` parameter remains optional
- Default behaviors are preserved for all existing field types

## Example Template

See `example_choiceOrder_template.json` for a complete example demonstrating the new functionality.
