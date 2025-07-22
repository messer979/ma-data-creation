"""
Functional template processing utilities
Contains pure functions for applying generation template rules to data
"""

import json
import random
import string
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from copy import deepcopy

# Import query context utilities for template generation
try:
    from data_creation.query_context_utils import (
        get_query_dataframe, 
        sample_from_query, 
        get_random_value_from_column,
        get_unique_column_values,
        filter_query_data,
        query_exists
    )
    QUERY_CONTEXT_AVAILABLE = True
except ImportError:
    QUERY_CONTEXT_AVAILABLE = False


def get_query_context_globals() -> Dict[str, Any]:
    """
    Get global variables for query context that can be used in template generation
    
    Returns:
        Dictionary of global variables including query utility functions
    """
    if not QUERY_CONTEXT_AVAILABLE:
        return {}
    
    return {
        'get_query_dataframe': get_query_dataframe,
        'sample_from_query': sample_from_query,
        'get_random_value_from_column': get_random_value_from_column,
        'get_unique_column_values': get_unique_column_values,
        'filter_query_data': filter_query_data,
        'query_exists': query_exists,
        # Add some convenience functions
        'random_facility': lambda: get_random_value_from_column('facilities', 'facility_id') if query_exists('facilities') else None,
        'random_item': lambda: get_random_value_from_column('items', 'item_id') if query_exists('items') else None,
        'random_vendor': lambda: get_random_value_from_column('vendors', 'vendor_id') if query_exists('vendors') else None,
    }


def apply_static_fields(record: Dict[str, Any], static_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply static field values to a record
    
    Args:
        record: The record to modify
        static_fields: Dictionary of field_name -> static_value
    
    Returns:
        Modified record
    """
    for field, value in static_fields.items():
        set_nested_field(record, field, value)
    return record


def process_dynamic_field_keywords(prefix: str) -> str:
    """
    Process keyword variables in dynamic field prefixes
    
    Args:
        prefix: The prefix string that may contain keyword variables
    
    Returns:
        Processed prefix with keyword variables replaced
    """
    processed = prefix
    
    # Replace {{dttm}} with current date in MMDD format
    if '{{dttm}}' in processed:
        current_date = datetime.now().strftime('%m%d')
        processed = processed.replace('{{dttm}}', current_date)
    return processed


def apply_sequence_fields(record: Dict[str, Any], 
                        sequence_fields: Dict[str, str], 
                        sequence_counters: Dict[str, int]) -> Dict[str, Any]:
    """
    Apply sequence (incremental) field values to a record
    
    Args:
        record: The record to modify
        sequence_fields: Dictionary of field_name -> prefix (supports {{dttm}} for current date MMDD)
        sequence_counters: Mutable dictionary tracking counters for each field
    
    Returns:
        Modified record
    """
    for field, prefix in sequence_fields.items():
        if field not in sequence_counters:
            sequence_counters[field] = 1
        else:
            sequence_counters[field] += 1
        
        # Process keyword variables in prefix
        processed_prefix = process_dynamic_field_keywords(prefix)
        
        generated_value = f"{processed_prefix}_{sequence_counters[field]:03d}"
        set_nested_field(record, field, generated_value)
    
    return record


def apply_random_fields(record: Dict[str, Any], random_fields: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Apply random field values to a record
    
    Args:
        record: The record to modify
        random_fields: List of field specifications with FieldName and FieldType
    
    Returns:
        Modified record
    """
    for field_spec in random_fields:
        field_name = field_spec['FieldName']
        field_type = field_spec['FieldType']
        random_value = generate_random_value(field_type)
        set_nested_field(record, field_name, random_value)
    
    return record


def apply_linked_fields(record: Dict[str, Any], linked_fields: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Apply linked field values derived from other fields
    
    Args:
        record: The record to modify
        linked_fields: Dictionary of source_field -> [linked_field_names]
    
    Returns:
        Modified record
    """
    for source_field, linked_field_names in linked_fields.items():
        source_value = get_nested_field(record, source_field)
        if source_value:
            for linked_field in linked_field_names:
                linked_value = generate_linked_value(source_value, linked_field)
                set_nested_field(record, linked_field, linked_value)
    
    return record


def set_nested_field(obj: Dict[str, Any], field_path: str, value: Any) -> None:
    """
    Set a nested field using dot notation
    
    Args:
        obj: Object to modify
        field_path: Dot notation path (e.g., "AsnLine.ItemId")
        value: Value to set
    """
    parts = field_path.split('.')
    current = obj
    
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            # This shouldn't happen in well-formed paths
            raise ValueError(f"Expected dict but found {type(current)} at path part '{part}'")
    
    # Set the final value
    final_field = parts[-1]
    if isinstance(current, dict):
        current[final_field] = value
    else:
        raise ValueError(f"Expected dict but found {type(current)} for field '{final_field}'")


def get_nested_field(obj: Dict[str, Any], field_path: str) -> Any:
    """
    Get a nested field using dot notation
    
    Args:
        obj: Object to read from
        field_path: Dot notation path (e.g., "AsnLine.ItemId")
    
    Returns:
        Field value or None if not found
    """
    parts = field_path.split('.')
    current = obj
    
    for part in parts:
        # Handle dictionary key access only
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    
    return current


def generate_random_value(field_type: str) -> Any:
    """
    Generate a random value based on field type specification
    
    Args:
        field_type: Type specification string (e.g., "float(2,3)", "string(12)", "boolean")
    
    Returns:
        Generated random value    """    # Parse field type patterns
    if field_type.startswith('float('):
        # Try float(low,high,precision) first - with whitespace handling
        match = re.match(r'float\(\s*(-?[0-9.]+)\s*,\s*(-?[0-9.]+)\s*,\s*(\d+)\s*\)', field_type)
        if match:
            low_val, high_val, precision = float(match.group(1)), float(match.group(2)), int(match.group(3))
            return round(random.uniform(low_val, high_val), precision)
        
        # Try float(low,high) with default precision - with whitespace handling
        match = re.match(r'float\(\s*(-?[0-9.]+)\s*,\s*(-?[0-9.]+)\s*\)', field_type)
        if match:
            low_val, high_val = float(match.group(1)), float(match.group(2))
            return round(random.uniform(low_val, high_val), 2)  # Default to 2 decimal places
    
    elif field_type == 'float':
        # Simple float type without parameters (0.0 to 100.0 with 2 decimal places)
        return round(random.uniform(0.0, 100.0), 2)
    
    elif field_type.startswith('int('):
        # First try int(min,max) format - with whitespace handling (supports negative numbers)
        match = re.match(r'int\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)', field_type)
        if match:
            min_val, max_val = int(match.group(1)), int(match.group(2))
            return random.randint(min_val, max_val)
        
        # Then try int(length) format for generating integers with specific character length
        length_match = re.match(r'int\(\s*(\d+)\s*\)', field_type)
        if length_match:
            length = int(length_match.group(1))
            if length <= 0:
                raise ValueError(f"Integer length must be positive, got {length}")
            # Generate a random integer with the specified number of digits
            # For length 1: 1-9, for length 2: 10-99, etc.
            if length == 1:
                return random.randint(1, 9)
            else:
                min_val = 10 ** (length - 1)
                max_val = (10 ** length) - 1
                return random.randint(min_val, max_val)
    
    elif field_type.startswith('string('):
        # string(length) - with whitespace handling
        match = re.match(r'string\(\s*(\d+)\s*\)', field_type)
        if match:
            length = int(match.group(1))
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    elif field_type == 'boolean':
        return random.choice([True, False])
    
    elif field_type.startswith('datetime('):
        # datetime(now), datetime(past), datetime(future), datetime(7) - with whitespace handling
        # First try to match numeric values like datetime(7) for specific days
        numeric_match = re.match(r'datetime\(\s*(-?\d+)\s*\)', field_type)
        if numeric_match:
            days_offset = int(numeric_match.group(1))
            target_date = datetime.now() + timedelta(days=days_offset)
            return target_date.isoformat()
        
        # Then try to match keyword values like datetime(now), datetime(past), datetime(future)
        keyword_match = re.match(r'datetime\(\s*(\w+)\s*\)', field_type)
        if keyword_match:
            time_type = keyword_match.group(1)
            if time_type == 'now':
                return datetime.now().isoformat()
            elif time_type == 'past':
                days_ago = random.randint(1, 365)
                past_date = datetime.now() - timedelta(days=days_ago)
                return past_date.isoformat()
            elif time_type == 'future':
                days_ahead = random.randint(1, 365)
                future_date = datetime.now() + timedelta(days=days_ahead)
                return future_date.isoformat()
    elif field_type.startswith('choice('):
        # choice(option1,option2,option3) - with whitespace handling
        match = re.match(r'choice\(\s*([^)]+)\s*\)', field_type)
        if match:
            choices = [choice.strip() for choice in match.group(1).split(',')]
            return random.choice(choices)
    
    elif field_type.startswith('choiceUnique('):
        # choiceUnique(option1,option2,option3) - with whitespace handling
        # Note: This function signature will be updated to support uniqueness context
        match = re.match(r'choiceUnique\(\s*([^)]+)\s*\)', field_type)
        if match:
            choices = [choice.strip() for choice in match.group(1).split(',')]
            # For now, return a random choice. The uniqueness logic will be handled
            # in the array processing functions that call this with additional context.
            return random.choice(choices)
    
    elif field_type == 'uuid':
        return str(uuid.uuid4())
    
    elif field_type == 'email':
        domains = ['example.com', 'test.com', 'demo.org']
        username = ''.join(random.choices(string.ascii_lowercase, k=8))
        return f"{username}@{random.choice(domains)}"
      # Default fallback
    return f"RANDOM_{random.randint(1000, 9999)}"


def generate_random_value_with_context(field_type: str, unique_context: Dict[str, set] = None, 
                                     field_path: str = None, array_path: str = None) -> Any:
    """
    Generate a random value based on field type specification with uniqueness context
    
    Args:
        field_type: Type specification string (e.g., "float(2,3)", "string(12)", "boolean", "choiceUnique(a,b,c)")
        unique_context: Dictionary tracking used values for choiceUnique fields per array context
        field_path: Full path of the field being generated (for uniqueness tracking)
        array_path: Path of the containing array (for uniqueness scope)
    
    Returns:
        Generated random value
    """
    # Handle choiceUnique with context
    if field_type.startswith('choiceUnique(') and unique_context is not None and field_path and array_path:
        match = re.match(r'choiceUnique\(\s*([^)]+)\s*\)', field_type)
        if match:
            choices = [choice.strip() for choice in match.group(1).split(',')]
            
            # Create a unique key for this field within this array context
            context_key = f"{array_path}.{field_path}"
            
            # Initialize the used set if not exists
            if context_key not in unique_context:
                unique_context[context_key] = set()
            
            # Get unused choices
            used_values = unique_context[context_key]
            unused_choices = [choice for choice in choices if choice not in used_values]
            
            # If we have unused choices, use one
            if unused_choices:
                selected_value = random.choice(unused_choices)
                unique_context[context_key].add(selected_value)
                return selected_value
            else:
                # All choices have been used, start reusing (fallback behavior)
                selected_value = random.choice(choices)
                return selected_value
    
    # For all other types (including regular choice and choiceUnique without context), 
    # fall back to the standard generate_random_value function
    return generate_random_value(field_type)


def generate_linked_value(source_value: str, linked_field: str) -> str:
    """
    Generate linked field values based on source field
    
    Args:
        source_value: Value from the source field
        linked_field: Name of the field to generate
    
    Returns:
        Generated linked value
    """
    return f"{source_value}"


def deep_copy_template(obj: Any) -> Any:
    """
    Deep copy object while preserving placeholder strings and structure
    
    Args:
        obj: Object to copy
    
    Returns:
        Deep copy of the object
    """
    if isinstance(obj, dict):
        return {k: deep_copy_template(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_copy_template(item) for item in obj]
    else:
        return obj


def parse_array_length_value(value) -> int:
    """
    Parse array length value, supporting both static integers and random int() expressions
    
    Args:
        value: The array length value - can be an integer or string like "int(1,10)"
    
    Returns:
        Resolved integer length
    """
    if isinstance(value, int):
        return value
    
    if isinstance(value, str):
        # Check for int(min,max) pattern
        match = re.match(r'int\(\s*(\d+)\s*,\s*(\d+)\s*\)', value.strip())
        if match:
            min_val, max_val = int(match.group(1)), int(match.group(2))
            return random.randint(min_val, max_val)
        
        # Try to convert plain string to integer
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid array length value: {value}. Must be an integer or 'int(min,max)' format.")
    
    raise ValueError(f"Invalid array length value type: {type(value)}. Must be an integer or string.")


def expand_nested_array(record: Dict[str, Any], array_path: str, array_length: int) -> None:
    """
    Expand a nested array (e.g., Lpn.LpnDetail) to the specified length.
    Supports up to 4 levels of nesting.
    
    Args:
        record: The record to modify
        array_path: The path to the nested array (e.g., "Lpn.LpnDetail")
        array_length: The desired length of the array
    """
    path_parts = array_path.split('.')
    
    def expand_at_path(current_obj, parts_remaining, depth=0):
        if depth > 4:  # Safety limit
            return
            
        if len(parts_remaining) == 1:
            # We've reached the final array to expand
            final_array_name = parts_remaining[0]
            
            if isinstance(current_obj, dict):
                if final_array_name in current_obj and isinstance(current_obj[final_array_name], list):
                    # Expand existing array
                    current_array = current_obj[final_array_name]
                    current_length = len(current_array)
                    if current_length < array_length:
                        # Use the first element as a template for new elements
                        template_element = current_array[0] if current_length > 0 else {}
                        for i in range(current_length, array_length):
                            current_array.append(deep_copy_template(template_element))
                    elif current_length > array_length:
                        # Truncate array if it's longer than needed
                        current_obj[final_array_name] = current_array[:array_length]
                elif final_array_name not in current_obj:
                    # Create new array with empty objects
                    current_obj[final_array_name] = [{} for _ in range(array_length)]
            elif isinstance(current_obj, list):
                # Current object is an array, expand the target array in each element
                for element in current_obj:
                    if isinstance(element, dict):
                        expand_at_path(element, parts_remaining, depth + 1)
            return
        
        # Navigate to the next level
        next_part = parts_remaining[0]
        remaining_parts = parts_remaining[1:]
        
        if isinstance(current_obj, dict) and next_part in current_obj:
            current_level = current_obj[next_part]
            if isinstance(current_level, list):
                # Current level is an array, expand in each element
                for element in current_level:
                    if isinstance(element, dict):
                        expand_at_path(element, remaining_parts, depth + 1)
            else:
                # Current level is a single object
                expand_at_path(current_level, remaining_parts, depth + 1)
    
    # Start expansion from the record
    expand_at_path(record, path_parts)


def create_record_from_template(base_template: Dict[str, Any], 
                              generation_template: Dict[str, Any],
                              index: int,
                              sequence_counters: Dict[str, int]) -> Dict[str, Any]:
    """
    Create a single record by applying generation template rules to base template
    
    Args:
        base_template: Base JSON template structure
        generation_template: Generation rules template
        index: Record index (0-based)
        sequence_counters: Mutable dictionary tracking sequence field counters
    
    Returns:
        Generated record
    """    
    # Start with a deep copy of the base template
    record = deep_copy_template(base_template)
    
    # Initialize unique context for choiceUnique fields
    unique_context = {}
      # Get array lengths configuration
    array_lengths = generation_template.get('ArrayLengths', {})
      # Initialize arrays to the specified lengths before processing fields
    for array_name, array_length_value in array_lengths.items():
        # Parse the array length value (supports both integers and random int() expressions)
        array_length = parse_array_length_value(array_length_value)
        
        if '.' in array_name:
            # Handle nested arrays (e.g., "Lpn.LpnDetail")
            expand_nested_array(record, array_name, array_length)
        elif array_name in record and isinstance(record[array_name], list):
            # Expand existing top-level array
            current_length = len(record[array_name])
            if current_length < array_length:
                # Use the first element as a template for new elements
                template_element = record[array_name][0] if current_length > 0 else {}
                for i in range(current_length, array_length):
                    record[array_name].append(deep_copy_template(template_element))
            elif current_length > array_length:
                # Truncate array if it's longer than needed
                record[array_name] = record[array_name][:array_length]
        elif array_name not in record:
            # Create new top-level array with empty objects
            record[array_name] = [{} for _ in range(array_length)]
    
    # Apply static fields with array handling
    if 'StaticFields' in generation_template:
        record = apply_static_fields_with_arrays(record, generation_template['StaticFields'], array_lengths)
    
    # Apply sequence fields with array handling
    if 'SequenceFields' in generation_template:
        record = apply_sequence_fields_with_arrays(record, generation_template['SequenceFields'], sequence_counters, array_lengths)
    
    # Apply random fields with array handling
    if 'RandomFields' in generation_template:
        record = apply_random_fields_with_arrays(record, generation_template['RandomFields'], array_lengths, unique_context)
    
    # Apply linked fields with array handling
    if 'LinkedFields' in generation_template:
        record = apply_linked_fields_with_arrays(record, generation_template['LinkedFields'], array_lengths)
    
    # Apply query context fields if available (new feature)
    if 'QueryContextFields' in generation_template and QUERY_CONTEXT_AVAILABLE:
        record = apply_query_context_fields_with_arrays(record, generation_template['QueryContextFields'], array_lengths)
    
    return record


def expand_fields_for_arrays(fields: Dict[str, Any], array_lengths: Dict[str, int]) -> Dict[str, Any]:
    """
    Since arrays are handled iteratively, just return fields as-is
    
    Args:
        fields: Dictionary of field definitions
        array_lengths: Dictionary of array_name -> length mappings (not used)
    
    Returns:
        Original fields dictionary unchanged
    """
    return fields


def expand_random_fields_for_arrays(random_fields: List[Dict[str, str]], array_lengths: Dict[str, int]) -> List[Dict[str, str]]:
    """
    Since arrays are handled iteratively, just return random fields as-is
    
    Args:
        random_fields: List of random field specifications
        array_lengths: Dictionary of array_name -> length mappings (not used)
    
    Returns:
        Original random fields list unchanged
    """
    return random_fields


def expand_linked_fields_for_arrays(linked_fields: Dict[str, List[str]], array_lengths: Dict[str, int]) -> Dict[str, List[str]]:
    """
    Since arrays are handled iteratively, just return linked fields as-is
    
    Args:
        linked_fields: Dictionary of source_field -> [linked_field_names]
        array_lengths: Dictionary of array_name -> length mappings (not used)
    
    Returns:
        Original linked fields dictionary unchanged
    """
    return linked_fields


def find_array_path_and_suffix(field_path: str, array_lengths: Dict[str, int]) -> tuple[str, str]:
    """
    Find the longest matching array path for a field and return the array path and remaining suffix.
    Supports up to 4 levels of nesting.
    
    Args:
        field_path: The full field path (e.g., "Lpn.LpnDetail.QuantityUomId")
        array_lengths: Dictionary of array_name -> length mappings
    
    Returns:
        Tuple of (array_path, field_suffix) where array_path is the longest matching array
        and field_suffix is the remaining path after the array
    """
    # Sort array paths by length (longest first) to match the most specific array path
    sorted_arrays = sorted(array_lengths.keys(), key=len, reverse=True)
    
    for array_path in sorted_arrays:
        if field_path.startswith(f"{array_path}."):
            field_suffix = field_path[len(array_path) + 1:]  # Remove "ArrayPath." prefix
            return array_path, field_suffix
    
    return None, field_path


def apply_to_nested_arrays(record: Dict[str, Any], array_path: str, field_suffix: str, 
                          value_func, *args) -> None:
    """
    Apply a function to nested array elements at the specified path.
    Supports up to 4 levels of nested arrays.
    
    Args:
        record: The record to modify
        array_path: The path to the array (e.g., "Lpn.LpnDetail")
        field_suffix: The field path within each array element
        value_func: Function to generate/get the value to set
        *args: Additional arguments to pass to value_func
    """
    # Split the array path into parts
    path_parts = array_path.split('.')
    
    def navigate_and_apply(current_obj, parts_remaining, depth=0):
        if depth > 4:  # Safety limit for recursion
            return
            
        if len(parts_remaining) == 1:
            # We're at the parent of the final array - navigate to the array itself
            final_array_name = parts_remaining[0]
            if isinstance(current_obj, dict) and final_array_name in current_obj:
                final_array = current_obj[final_array_name]
                if isinstance(final_array, list):
                    # Apply to all elements in the final array
                    for element in final_array:
                        if isinstance(element, dict):
                            # Generate a fresh value for each array element
                            if args:
                                value = value_func(*args)
                            else:
                                value = value_func()
                            set_nested_field(element, field_suffix, value)
            elif isinstance(current_obj, list):
                # Current object is an array, apply to final array in each element
                for element in current_obj:
                    if isinstance(element, dict) and final_array_name in element:
                        final_array = element[final_array_name]
                        if isinstance(final_array, list):
                            for sub_element in final_array:
                                if isinstance(sub_element, dict):
                                    if args:
                                        value = value_func(*args)
                                    else:
                                        value = value_func()
                                    set_nested_field(sub_element, field_suffix, value)
            return
        
        # Navigate to the next level (not the final array yet)
        next_part = parts_remaining[0]
        remaining_parts = parts_remaining[1:]
        
        if isinstance(current_obj, dict) and next_part in current_obj:
            current_level = current_obj[next_part]
            if isinstance(current_level, list):
                # Current level is an array, iterate through its elements
                for element in current_level:
                    if isinstance(element, dict):
                        navigate_and_apply(element, remaining_parts, depth + 1)
            else:
                # Current level is a single object
                navigate_and_apply(current_level, remaining_parts, depth + 1)
        elif isinstance(current_obj, list):
            # Current object is already an array, process each element
            for element in current_obj:
                if isinstance(element, dict) and next_part in element:
                    next_level = element[next_part]
                    if isinstance(next_level, list):
                        # Navigate into the next array level
                        for sub_element in next_level:
                            if isinstance(sub_element, dict):
                                navigate_and_apply(sub_element, remaining_parts, depth + 1)
                    else:
                        navigate_and_apply(next_level, remaining_parts, depth + 1)
    
    # Start navigation from the record
    navigate_and_apply(record, path_parts)


def apply_static_fields_with_arrays(record: Dict[str, Any], 
                                   static_fields: Dict[str, Any], 
                                   array_lengths: Dict[str, int]) -> Dict[str, Any]:
    """
    Apply static field values to a record, handling multi-level array fields by iterating over array elements
    
    Args:
        record: The record to modify
        static_fields: Dictionary of field_name -> static_value
        array_lengths: Dictionary of array_name -> length mappings
    
    Returns:
        Modified record
    """
    for field, value in static_fields.items():
        if '.' in field:
            # Check if this field references any array (including nested arrays)
            array_path, field_suffix = find_array_path_and_suffix(field, array_lengths)
            
            if array_path:
                # This is an array field - apply to all nested array elements
                apply_to_nested_arrays(record, array_path, field_suffix, lambda: value)
            else:
                # Regular nested field
                set_nested_field(record, field, value)
        else:
            # Simple field
            set_nested_field(record, field, value)
    
    return record


def apply_sequence_fields_with_arrays(record: Dict[str, Any], 
                                   sequence_fields: Dict[str, str], 
                                   sequence_counters: Dict[str, int],
                                   array_lengths: Dict[str, int]) -> Dict[str, Any]:
    """
    Apply sequence field values to a record, handling multi-level array fields by iterating over array elements
    
    Args:
        record: The record to modify
        sequence_fields: Dictionary of field_name -> prefix
        sequence_counters: Mutable dictionary tracking counters for each field
        array_lengths: Dictionary of array_name -> length mappings
    
    Returns:
        Modified record
    """
    for field, prefix in sequence_fields.items():
        # Process keyword variables in prefix
        processed_prefix = process_dynamic_field_keywords(prefix)
        
        if '.' in field:
            # Check if this field references any array (including nested arrays)
            array_path, field_suffix = find_array_path_and_suffix(field, array_lengths)
            
            if array_path:
                # This is an array field - apply per-element indexing for nested arrays
                def generate_dynamic_value_for_element():
                    # For array elements, use sequential indexing within this record
                    # We'll track the index during application
                    return None  # Placeholder, actual value set in apply_to_nested_arrays_with_index
                
                apply_to_nested_arrays_with_index(record, array_path, field_suffix, processed_prefix)
            else:
                # Regular nested field - use global counter
                if field not in sequence_counters:
                    sequence_counters[field] = 1
                else:
                    sequence_counters[field] += 1
                
                generated_value = f"{processed_prefix}_{sequence_counters[field]:03d}"
                set_nested_field(record, field, generated_value)
        else:
            # Simple field - use global counter
            if field not in sequence_counters:
                sequence_counters[field] = 1
            else:
                sequence_counters[field] += 1
            
            generated_value = f"{processed_prefix}_{sequence_counters[field]:03d}"
            set_nested_field(record, field, generated_value)
    
    return record


def apply_to_nested_arrays_with_index(record: Dict[str, Any], array_path: str, field_suffix: str, 
                                     prefix: str) -> None:
    """
    Apply dynamic values to nested array elements with per-element indexing.
    Supports up to 4 levels of nested arrays.
    
    Args:
        record: The record to modify
        array_path: The path to the array (e.g., "Lpn.LpnDetail")
        field_suffix: The field path within each array element
        prefix: The prefix for generating dynamic values
    """
    # Split the array path into parts
    path_parts = array_path.split('.')
    
    def navigate_and_apply_with_index(current_obj, parts_remaining, depth=0, indices=[]):
        if depth > 4:  # Safety limit for recursion
            return
            
        if len(parts_remaining) == 1:
            # We're at the parent of the final array - navigate to the array itself
            final_array_name = parts_remaining[0]
            if isinstance(current_obj, dict) and final_array_name in current_obj:
                final_array = current_obj[final_array_name]
                if isinstance(final_array, list):
                    # Apply to all elements in the final array
                    for i, element in enumerate(final_array):
                        if isinstance(element, dict):
                            # Use 1-based indexing for the element
                            element_index = i + 1
                            element_value = f"{prefix}_{element_index:03d}"
                            set_nested_field(element, field_suffix, element_value)
            elif isinstance(current_obj, list):
                # Current object is an array, apply to final array in each element
                for element in current_obj:
                    if isinstance(element, dict) and final_array_name in element:
                        final_array = element[final_array_name]
                        if isinstance(final_array, list):
                            for i, sub_element in enumerate(final_array):
                                if isinstance(sub_element, dict):
                                    element_index = i + 1
                                    element_value = f"{prefix}_{element_index:03d}"
                                    set_nested_field(sub_element, field_suffix, element_value)
            return
        
        # Navigate to the next level (not the final array yet)
        next_part = parts_remaining[0]
        remaining_parts = parts_remaining[1:]
        
        if isinstance(current_obj, dict) and next_part in current_obj:
            current_level = current_obj[next_part]
            if isinstance(current_level, list):
                # Current level is an array, iterate through its elements
                for i, element in enumerate(current_level):
                    if isinstance(element, dict):
                        navigate_and_apply_with_index(element, remaining_parts, depth + 1, indices + [i])
            else:
                # Current level is a single object
                navigate_and_apply_with_index(current_level, remaining_parts, depth + 1, indices)
    
    # Start navigation from the record
    navigate_and_apply_with_index(record, path_parts)


def apply_random_fields_with_arrays(record: Dict[str, Any], 
                                  random_fields: List[Dict[str, str]],
                                  array_lengths: Dict[str, int],
                                  unique_context: Dict[str, set] = None) -> Dict[str, Any]:
    """
    Apply random field values to a record, handling multi-level array fields by iterating over array elements
    
    Args:
        record: The record to modify
        random_fields: List of field specifications with FieldName and FieldType
        array_lengths: Dictionary of array_name -> length mappings
        unique_context: Dictionary tracking used values for choiceUnique fields per array context
    
    Returns:
        Modified record
    """
    # Initialize unique context if not provided
    if unique_context is None:
        unique_context = {}
    
    for field_spec in random_fields:
        field_name = field_spec['FieldName']
        field_type = field_spec['FieldType']
        
        if '.' in field_name:
            # Check if this field references any array (including nested arrays)
            array_path, field_suffix = find_array_path_and_suffix(field_name, array_lengths)
            
            if array_path:
                # This is an array field - check if it's a choiceUnique field
                if field_type.startswith('choiceUnique('):
                    # Use unique context functionality for choiceUnique fields
                    apply_to_nested_arrays_with_unique_context(record, array_path, field_suffix, field_type, unique_context)
                else:
                    # Regular array field - apply to all nested array elements with different random values
                    apply_to_nested_arrays(record, array_path, field_suffix, generate_random_value, field_type)
            else:
                # Regular nested field
                random_value = generate_random_value(field_type)
                set_nested_field(record, field_name, random_value)
        else:
            # Simple field
            random_value = generate_random_value(field_type)
            set_nested_field(record, field_name, random_value)
    
    return record


def apply_linked_fields_with_arrays(record: Dict[str, Any], 
                                  linked_fields: Dict[str, List[str]],
                                  array_lengths: Dict[str, int]) -> Dict[str, Any]:
    """
    Apply linked field values derived from other fields, handling multi-level array fields by iterating over array elements
    
    Args:
        record: The record to modify
        linked_fields: Dictionary of source_field -> [linked_field_names]
        array_lengths: Dictionary of array_name -> length mappings
    
    Returns:
        Modified record
    """
    for source_field, linked_field_names in linked_fields.items():
        # Check if source field is within an array
        if '.' in source_field:
            source_array_path, source_field_suffix = find_array_path_and_suffix(source_field, array_lengths)
            
            if source_array_path:
                # Source field is within an array - need to handle element-by-element linking
                for linked_field in linked_field_names:
                    apply_array_to_array_linking(record, source_array_path, source_field_suffix, 
                                               linked_field, array_lengths)
            else:
                # Source field is not in an array - use the original logic
                source_value = get_nested_field(record, source_field)
                if source_value:
                    for linked_field in linked_field_names:
                        linked_value = generate_linked_value(source_value, linked_field)
                        
                        if '.' in linked_field:
                            # Check if this field references any array (including nested arrays)
                            array_path, field_suffix = find_array_path_and_suffix(linked_field, array_lengths)
                            
                            if array_path:
                                # This is an array field - apply to all nested array elements
                                apply_to_nested_arrays(record, array_path, field_suffix, lambda: linked_value)
                            else:
                                # Regular nested field
                                set_nested_field(record, linked_field, linked_value)
                        else:
                            # Simple field
                            set_nested_field(record, linked_field, linked_value)
        else:
            # Simple source field - use the original logic
            source_value = get_nested_field(record, source_field)
            if source_value:
                for linked_field in linked_field_names:
                    linked_value = generate_linked_value(source_value, linked_field)
                    
                    if '.' in linked_field:
                        # Check if this field references any array (including nested arrays)
                        array_path, field_suffix = find_array_path_and_suffix(linked_field, array_lengths)
                        
                        if array_path:
                            # This is an array field - apply to all nested array elements
                            apply_to_nested_arrays(record, array_path, field_suffix, lambda: linked_value)
                        else:
                            # Regular nested field
                            set_nested_field(record, linked_field, linked_value)
                    else:
                        # Simple field
                        set_nested_field(record, linked_field, linked_value)
    
    return record


def apply_array_to_array_linking(record: Dict[str, Any], source_array_path: str, source_field_suffix: str,
                                linked_field: str, array_lengths: Dict[str, int]) -> None:
    """
    Apply linking from an array field to another field (which may also be in an array).
    This handles cases like linking Lpn.LpnDetail.ItemId to Lpn.LpnDetail.LpnDetailGroupingId.
    
    Args:
        record: The record to modify
        source_array_path: The path to the source array (e.g., "Lpn.LpnDetail")
        source_field_suffix: The field path within each source array element
        linked_field: The target field to set
        array_lengths: Dictionary of array_name -> length mappings
    """
    # Check if the linked field is also within an array
    if '.' in linked_field:
        linked_array_path, linked_field_suffix = find_array_path_and_suffix(linked_field, array_lengths)
        
        if linked_array_path and linked_array_path == source_array_path:
            # Both source and linked fields are in the same array - element-to-element linking
            apply_element_to_element_linking(record, source_array_path, source_field_suffix, linked_field_suffix)
        elif linked_array_path:
            # Source and linked fields are in different arrays - this is more complex
            # For now, we'll apply the first source value to all linked array elements
            source_values = get_all_array_field_values(record, source_array_path, source_field_suffix)
            if source_values:
                first_source_value = source_values[0]
                linked_value = generate_linked_value(first_source_value, linked_field)
                apply_to_nested_arrays(record, linked_array_path, linked_field_suffix, lambda: linked_value)
        else:
            # Linked field is not in an array - use first source value
            source_values = get_all_array_field_values(record, source_array_path, source_field_suffix)
            if source_values:
                first_source_value = source_values[0]
                linked_value = generate_linked_value(first_source_value, linked_field)
                set_nested_field(record, linked_field, linked_value)
    else:
        # Linked field is a simple field - use first source value
        source_values = get_all_array_field_values(record, source_array_path, source_field_suffix)
        if source_values:
            first_source_value = source_values[0]
            linked_value = generate_linked_value(first_source_value, linked_field)
            set_nested_field(record, linked_field, linked_value)


def apply_element_to_element_linking(record: Dict[str, Any], array_path: str, 
                                   source_field_suffix: str, linked_field_suffix: str) -> None:
    """
    Apply element-to-element linking within the same array.
    For each array element, take the source field value and set the linked field value.
    
    Args:
        record: The record to modify
        array_path: The path to the array (e.g., "Lpn.LpnDetail")
        source_field_suffix: The source field path within each array element
        linked_field_suffix: The linked field path within each array element
    """
    # Split the array path into parts
    path_parts = array_path.split('.')
    
    def navigate_and_link(current_obj, parts_remaining, depth=0):
        if depth > 4:  # Safety limit for recursion
            return
            
        if len(parts_remaining) == 1:
            # We're at the parent of the final array - navigate to the array itself
            final_array_name = parts_remaining[0]
            if isinstance(current_obj, dict) and final_array_name in current_obj:
                final_array = current_obj[final_array_name]
                if isinstance(final_array, list):
                    # Process each element in the final array
                    for element in final_array:
                        if isinstance(element, dict):
                            # Get source value from this element
                            source_value = get_nested_field(element, source_field_suffix)
                            if source_value:
                                # Generate linked value and set it in this element
                                linked_value = generate_linked_value(source_value, linked_field_suffix)
                                set_nested_field(element, linked_field_suffix, linked_value)
            elif isinstance(current_obj, list):
                # Current object is an array, process final array in each element
                for element in current_obj:
                    if isinstance(element, dict) and final_array_name in element:
                        final_array = element[final_array_name]
                        if isinstance(final_array, list):
                            for sub_element in final_array:
                                if isinstance(sub_element, dict):
                                    source_value = get_nested_field(sub_element, source_field_suffix)
                                    if source_value:
                                        linked_value = generate_linked_value(source_value, linked_field_suffix)
                                        set_nested_field(sub_element, linked_field_suffix, linked_value)
            return
        
        # Navigate to the next level (not the final array yet)
        next_part = parts_remaining[0]
        remaining_parts = parts_remaining[1:]
        
        if isinstance(current_obj, dict) and next_part in current_obj:
            current_level = current_obj[next_part]
            if isinstance(current_level, list):
                # Current level is an array, iterate through its elements
                for element in current_level:
                    if isinstance(element, dict):
                        navigate_and_link(element, remaining_parts, depth + 1)
            else:
                # Current level is a single object
                navigate_and_link(current_level, remaining_parts, depth + 1)
    
    # Start navigation from the record
    navigate_and_link(record, path_parts)


def get_all_array_field_values(record: Dict[str, Any], array_path: str, field_suffix: str) -> List[Any]:
    """
    Get all values of a field from all elements in an array.
    
    Args:
        record: The record to read from
        array_path: The path to the array (e.g., "Lpn.LpnDetail")
        field_suffix: The field path within each array element
    
    Returns:
        List of all values found (may be empty)
    """
    values = []
    path_parts = array_path.split('.')
    
    def navigate_and_collect(current_obj, parts_remaining, depth=0):
        if depth > 4:  # Safety limit for recursion
            return
            
        if len(parts_remaining) == 1:
            # We're at the parent of the final array - navigate to the array itself
            final_array_name = parts_remaining[0]
            if isinstance(current_obj, dict) and final_array_name in current_obj:
                final_array = current_obj[final_array_name]
                if isinstance(final_array, list):
                    # Collect values from each element in the final array
                    for element in final_array:
                        if isinstance(element, dict):
                            value = get_nested_field(element, field_suffix)
                            if value is not None:
                                values.append(value)
            elif isinstance(current_obj, list):
                # Current object is an array, collect from final array in each element
                for element in current_obj:
                    if isinstance(element, dict) and final_array_name in element:
                        final_array = element[final_array_name]
                        if isinstance(final_array, list):
                            for sub_element in final_array:
                                if isinstance(sub_element, dict):
                                    value = get_nested_field(sub_element, field_suffix)
                                    if value is not None:
                                        values.append(value)
            return
        
        # Navigate to the next level (not the final array yet)
        next_part = parts_remaining[0]
        remaining_parts = parts_remaining[1:]
        
        if isinstance(current_obj, dict) and next_part in current_obj:
            current_level = current_obj[next_part]
            if isinstance(current_level, list):
                # Current level is an array, iterate through its elements
                for element in current_level:
                    if isinstance(element, dict):
                        navigate_and_collect(element, remaining_parts, depth + 1)
            else:
                # Current level is a single object
                navigate_and_collect(current_level, remaining_parts, depth + 1)
    
    # Start navigation from the record
    navigate_and_collect(record, path_parts)
    return values


def apply_to_nested_arrays_with_unique_context(record: Dict[str, Any], array_path: str, field_suffix: str, 
                                              field_type: str, unique_context: Dict[str, set]) -> None:
    """
    Apply choiceUnique values to nested array elements with uniqueness tracking.
    Supports up to 4 levels of nested arrays.
    
    Args:
        record: The record to modify
        array_path: The path to the array (e.g., "Lpn.LpnDetail")
        field_suffix: The field path within each array element
        field_type: The field type specification (should be choiceUnique)
        unique_context: Dictionary tracking used values for choiceUnique fields per array context
    """
    # Split the array path into parts
    path_parts = array_path.split('.')
    
    def navigate_and_apply_unique(current_obj, parts_remaining, depth=0):
        if depth > 4:  # Safety limit for recursion
            return
            
        if len(parts_remaining) == 1:
            # We're at the parent of the final array - navigate to the array itself
            final_array_name = parts_remaining[0]
            if isinstance(current_obj, dict) and final_array_name in current_obj:
                final_array = current_obj[final_array_name]
                if isinstance(final_array, list):
                    # Apply to all elements in the final array with unique context
                    for element in final_array:
                        if isinstance(element, dict):
                            # Generate a unique value for each array element
                            value = generate_random_value_with_context(
                                field_type, unique_context, field_suffix, array_path
                            )
                            set_nested_field(element, field_suffix, value)
            elif isinstance(current_obj, list):
                # Current object is an array, apply to final array in each element
                for element in current_obj:
                    if isinstance(element, dict) and final_array_name in element:
                        final_array = element[final_array_name]
                        if isinstance(final_array, list):
                            for sub_element in final_array:
                                if isinstance(sub_element, dict):
                                    value = generate_random_value_with_context(
                                        field_type, unique_context, field_suffix, array_path
                                    )
                                    set_nested_field(sub_element, field_suffix, value)
            return
        
        # Navigate to the next level (not the final array yet)
        next_part = parts_remaining[0]
        remaining_parts = parts_remaining[1:]
        
        if isinstance(current_obj, dict) and next_part in current_obj:
            current_level = current_obj[next_part]
            if isinstance(current_level, list):
                # Current level is an array, iterate through its elements
                for element in current_level:
                    if isinstance(element, dict):
                        navigate_and_apply_unique(element, remaining_parts, depth + 1)
            else:
                # Current level is a single object
                navigate_and_apply_unique(current_level, remaining_parts, depth + 1)
        elif isinstance(current_obj, list):
            # Current object is already an array, process each element
            for element in current_obj:
                if isinstance(element, dict) and next_part in element:
                    next_level = element[next_part]
                    if isinstance(next_level, list):
                        # Navigate into the next array level
                        for sub_element in next_level:
                            if isinstance(sub_element, dict):
                                navigate_and_apply_unique(sub_element, remaining_parts, depth + 1)
                    else:
                        navigate_and_apply_unique(next_level, remaining_parts, depth + 1)
    
    # Start navigation from the record
    navigate_and_apply_unique(record, path_parts)


def apply_query_context_fields_with_arrays(record: Dict[str, Any], 
                                         query_context_fields: Dict[str, Any], 
                                         array_lengths: Dict[str, int]) -> Dict[str, Any]:
    """
    Apply query context fields to a record with array handling
    
    Args:
        record: The record to modify
        query_context_fields: Dictionary of field_name -> query specification
        array_lengths: Dictionary of array_name -> length mappings
    
    Returns:
        Modified record
    """
    for field_name, query_spec in query_context_fields.items():
        # Find the array path and field suffix
        array_path, field_suffix = find_array_path_and_suffix(field_name, array_lengths)
        
        if array_path:
            # Handle array field
            apply_query_context_field_to_array(record, array_path, field_suffix, query_spec)
        else:
            # Handle non-array field
            apply_query_context_field(record, field_name, query_spec)
    
    return record


def apply_query_context_field_to_array(record: Dict[str, Any], 
                                     array_path: str, 
                                     field_suffix: str, 
                                     query_spec: Dict[str, Any]):
    """
    Apply query context field to all elements in an array
    
    Args:
        record: The record containing the array
        array_path: Path to the array in the record
        field_suffix: Field name within each array element
        query_spec: Query specification dictionary
    """
    def apply_to_array_elements(current_obj: Dict[str, Any], path_parts: List[str], depth: int = 0):
        if depth >= len(path_parts):
            # We've reached the target array level
            if isinstance(current_obj, list):
                # Apply to each element in the array
                for element in current_obj:
                    if isinstance(element, dict):
                        apply_query_context_field(element, field_suffix, query_spec)
            return
        
        current_part = path_parts[depth]
        
        if current_part in current_obj:
            apply_to_array_elements(current_obj[current_part], path_parts, depth + 1)
    
    # Split array path and apply
    path_parts = array_path.split('.')
    apply_to_array_elements(record, path_parts)


def apply_operation_to_value(value: Any, operation: str) -> Any:
    """
    Apply a mathematical operation to a value
    
    Args:
        value: The value to operate on
        operation: The operation string (e.g., "*5", "+10", "-3", "/2", "%100")
        
    Returns:
        The result of the operation, or original value if operation fails
    """
    try:
        # Parse the operation
        if not operation or not isinstance(operation, str):
            return value
            
        operation = operation.strip()
        if not operation:
            return value
            
        # Extract operator and operand
        operator = operation[0]
        operand_str = operation[1:].strip()
        
        if not operand_str:
            return value
        
        # Check if operand is a range format like (1,5) or (200,1000)
        range_pattern = r'^\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)$'
        range_match = re.match(range_pattern, operand_str)
        if range_match:
            # Parse range format: (min,max)
            try:
                min_str, max_str = range_match.groups()
                
                # Try to parse as integers first
                if '.' not in min_str and '.' not in max_str:
                    min_val = int(min_str)
                    max_val = int(max_str)
                    operand = random.randint(min_val, max_val)
                else:
                    # Parse as floats
                    min_val = float(min_str)
                    max_val = float(max_str)
                    operand = random.uniform(min_val, max_val)
            except (ValueError, IndexError):
                return value  # Invalid range format
        else:
            # Single value format - handle multi-digit numbers and floats
            try:
                # Try integer first (supports negative numbers)
                if '.' not in operand_str:
                    operand = int(operand_str)
                else:
                    # Try float
                    operand = float(operand_str)
            except ValueError:
                # Invalid operand
                return value
        
        # Convert value to number if it's not already
        try:
            if isinstance(value, (int, float)):
                numeric_value = value
            else:
                # Try to convert string to number
                try:
                    numeric_value = int(value)
                except ValueError:
                    numeric_value = float(value)
        except (ValueError, TypeError):
            # Value cannot be converted to number
            return value
        # Apply the operation
        if operator == '+':
            result = numeric_value + operand
        elif operator == '-':
            result = numeric_value - operand
        elif operator == '*':
            result = numeric_value * operand
        elif operator == '/':
            if operand == 0:
                return value  # Avoid division by zero
            result = numeric_value / operand
        elif operator == '%':
            if operand == 0:
                return value  # Avoid modulo by zero
            result = numeric_value % operand
        elif operator == '^' or operator == '**':
            result = numeric_value ** operand
        else:
            # Unknown operator
            return value
        # Preserve the original type if possible
        if isinstance(value, int) and isinstance(result, float) and result.is_integer():
            return int(result)
        else:
            return result
            
    except Exception:
        # If any error occurs, return the original value
        return value


def apply_query_context_field(record: Dict[str, Any], field_name: str, query_spec: Dict[str, Any]):
    """
    Apply a single query context field to a record
    
    Args:
        record: The record to modify
        field_name: Name of the field to set
        query_spec: Query specification with 'query', 'column', and optional 'mode', 'template_key', 'query_key'
    """
    if not QUERY_CONTEXT_AVAILABLE:
        return
    
    try:
        query_name = query_spec.get('query')
        column_name = query_spec.get('column')
        mode = query_spec.get('mode', 'random')  # 'random', 'unique', 'sequential', 'match'
        
        if not query_name or not column_name:
            return
        
        if not query_exists(query_name):
            return
        
        # Get value based on mode
        if mode == 'match':
            # New match mode - lookup based on template and query keys
            template_key = query_spec.get('template_key')
            query_key = query_spec.get('query_key')
            if not template_key or not query_key:
                return
                
            # Get the value from the template to match against
            template_value = get_nested_field(record, template_key)
            if template_value is None:
                return
                
            # Get the dataframe and find matching row
            df = get_query_dataframe(query_name)
            if df is None or df.empty:
                return
                
            # Find row where query_key column matches template_value
            matching_rows = df[df[query_key] == template_value]
            if not matching_rows.empty:
                # Use the first matching row
                value = matching_rows[column_name].iloc[0]
            else:
                # No match found, could fall back to random or return None
                value = None
                
        elif mode == 'random':
            value = get_random_value_from_column(query_name, column_name)
        elif mode == 'unique':
            # For unique mode, get all unique values and choose randomly
            unique_values = get_unique_column_values(query_name, column_name)
            if unique_values:
                value = random.choice(unique_values)
            else:
                value = None
        elif mode == 'sequential':
            # For sequential mode, get all values and choose based on some sequence
            # This is a simplified implementation - could be enhanced
            all_values = get_unique_column_values(query_name, column_name)
            if all_values:
                # Use field name hash for consistent selection
                import hashlib
                field_hash = int(hashlib.md5(field_name.encode()).hexdigest(), 16)
                index = field_hash % len(all_values)
                value = all_values[index]
            else:
                value = None
        else:
            value = get_random_value_from_column(query_name, column_name)
        
        # Apply operation if specified and value is not None
        if value is not None:
            operation = query_spec.get('operation')
            if operation:
                value = apply_operation_to_value(value, operation)
        
        if value is not None:
            set_nested_field(record, field_name, value)
            
    except Exception as e:
        # Silently fail for query context errors to avoid breaking data generation
        pass
