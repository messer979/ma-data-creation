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


def apply_dynamic_fields(record: Dict[str, Any], 
                        dynamic_fields: Dict[str, str], 
                        dynamic_counters: Dict[str, int]) -> Dict[str, Any]:
    """
    Apply dynamic (incremental) field values to a record
    
    Args:
        record: The record to modify
        dynamic_fields: Dictionary of field_name -> prefix (supports {{dttm}} for current date MMDD)
        dynamic_counters: Mutable dictionary tracking counters for each field
    
    Returns:
        Modified record
    """
    for field, prefix in dynamic_fields.items():
        if field not in dynamic_counters:
            dynamic_counters[field] = 1
        else:
            dynamic_counters[field] += 1
        
        # Process keyword variables in prefix
        processed_prefix = process_dynamic_field_keywords(prefix)
        
        generated_value = f"{processed_prefix}_{dynamic_counters[field]:03d}"
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
        match = re.match(r'float\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*(\d+)\s*\)', field_type)
        if match:
            low_val, high_val, precision = float(match.group(1)), float(match.group(2)), int(match.group(3))
            return round(random.uniform(low_val, high_val), precision)
        
        # Try float(low,high) with default precision - with whitespace handling
        match = re.match(r'float\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)', field_type)
        if match:
            low_val, high_val = float(match.group(1)), float(match.group(2))
            return round(random.uniform(low_val, high_val), 2)  # Default to 2 decimal places
    
    elif field_type == 'float':
        # Simple float type without parameters (0.0 to 100.0 with 2 decimal places)
        return round(random.uniform(0.0, 100.0), 2)
    
    elif field_type.startswith('int('):
        # int(min,max) - with whitespace handling
        match = re.match(r'int\(\s*(\d+)\s*,\s*(\d+)\s*\)', field_type)
        if match:
            min_val, max_val = int(match.group(1)), int(match.group(2))
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
        # datetime(now), datetime(past), datetime(future) - with whitespace handling
        match = re.match(r'datetime\(\s*(\w+)\s*\)', field_type)
        if match:
            time_type = match.group(1)
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


def apply_to_nested_arrays_with_unique_context(record: Dict[str, Any], array_path: str, field_suffix: str, 
                                              field_type: str, unique_context: Dict[str, set]) -> None:
    """
    Apply random values with uniqueness context to nested array elements at the specified path.
    Supports up to 4 levels of nested arrays. For choiceUnique fields, ensures uniqueness within sibling arrays.
    
    Args:
        record: The record to modify
        array_path: The path to the array (e.g., "Lpn.LpnDetail")
        field_suffix: The field path within each array element
        field_type: The field type specification (e.g., "choiceUnique(a,b,c)")
        unique_context: Dictionary tracking used values for choiceUnique fields per array context
    """
    # Split the array path into parts
    path_parts = array_path.split('.')
    
    def navigate_and_apply_unique(current_obj, parts_remaining, current_array_path="", depth=0):
        if depth > 4:  # Safety limit for recursion
            return
            
        if len(parts_remaining) == 1:
            # We're at the parent of the final array - navigate to the array itself
            final_array_name = parts_remaining[0]
            final_array_path = f"{current_array_path}.{final_array_name}" if current_array_path else final_array_name
            
            if isinstance(current_obj, dict) and final_array_name in current_obj:
                final_array = current_obj[final_array_name]
                if isinstance(final_array, list):
                    # Apply to all elements in the final array with unique context
                    for element in final_array:
                        if isinstance(element, dict):
                            value = generate_random_value_with_context(
                                field_type, unique_context, field_suffix, final_array_path
                            )
                            set_nested_field(element, field_suffix, value)
            elif isinstance(current_obj, list):
                # Current object is an array, apply to final array in each element
                for i, element in enumerate(current_obj):
                    if isinstance(element, dict) and final_array_name in element:
                        final_array = element[final_array_name]
                        if isinstance(final_array, list):
                            # Each parent array element gets its own unique context
                            element_array_path = f"{current_array_path}[{i}].{final_array_name}"
                            for sub_element in final_array:
                                if isinstance(sub_element, dict):
                                    value = generate_random_value_with_context(
                                        field_type, unique_context, field_suffix, element_array_path
                                    )
                                    set_nested_field(sub_element, field_suffix, value)
            return
        
        # Navigate to the next level (not the final array yet)
        next_part = parts_remaining[0]
        remaining_parts = parts_remaining[1:]
        next_array_path = f"{current_array_path}.{next_part}" if current_array_path else next_part
        
        if isinstance(current_obj, dict) and next_part in current_obj:
            current_level = current_obj[next_part]
            if isinstance(current_level, list):
                # Current level is an array, iterate through its elements
                for i, element in enumerate(current_level):
                    if isinstance(element, dict):
                        element_array_path = f"{next_array_path}[{i}]"
                        navigate_and_apply_unique(element, remaining_parts, element_array_path, depth + 1)
            else:
                # Current level is a single object
                navigate_and_apply_unique(current_level, remaining_parts, next_array_path, depth + 1)
        elif isinstance(current_obj, list):
            # Current object is already an array, process each element
            for i, element in enumerate(current_obj):
                if isinstance(element, dict) and next_part in element:
                    next_level = element[next_part]
                    element_array_path = f"{current_array_path}[{i}].{next_part}"
                    if isinstance(next_level, list):
                        # Navigate into the next array level
                        for j, sub_element in enumerate(next_level):
                            if isinstance(sub_element, dict):
                                sub_element_array_path = f"{element_array_path}[{j}]"
                                navigate_and_apply_unique(sub_element, remaining_parts, sub_element_array_path, depth + 1)
                    else:
                        navigate_and_apply_unique(next_level, remaining_parts, element_array_path, depth + 1)
    
    # Start navigation from the record
    navigate_and_apply_unique(record, path_parts)


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
                              dynamic_counters: Dict[str, int]) -> Dict[str, Any]:
    """
    Create a single record by applying generation template rules to base template
    
    Args:
        base_template: Base JSON template structure
        generation_template: Generation rules template
        index: Record index (0-based)
        dynamic_counters: Mutable dictionary tracking dynamic field counters
    
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
    
    # Apply dynamic fields with array handling
    if 'DynamicFields' in generation_template:
        record = apply_dynamic_fields_with_arrays(record, generation_template['DynamicFields'], dynamic_counters, array_lengths)
    
    # Apply random fields with array handling
    if 'RandomFields' in generation_template:
        record = apply_random_fields_with_arrays(record, generation_template['RandomFields'], array_lengths, unique_context)
    
    # Apply linked fields with array handling
    if 'LinkedFields' in generation_template:
        record = apply_linked_fields_with_arrays(record, generation_template['LinkedFields'], array_lengths)
    
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


def apply_dynamic_fields_with_arrays(record: Dict[str, Any], 
                                   dynamic_fields: Dict[str, str], 
                                   dynamic_counters: Dict[str, int],
                                   array_lengths: Dict[str, int]) -> Dict[str, Any]:
    """
    Apply dynamic field values to a record, handling multi-level array fields by iterating over array elements
    
    Args:
        record: The record to modify
        dynamic_fields: Dictionary of field_name -> prefix
        dynamic_counters: Mutable dictionary tracking counters for each field
        array_lengths: Dictionary of array_name -> length mappings
    
    Returns:
        Modified record
    """
    for field, prefix in dynamic_fields.items():
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
                if field not in dynamic_counters:
                    dynamic_counters[field] = 1
                else:
                    dynamic_counters[field] += 1
                
                generated_value = f"{processed_prefix}_{dynamic_counters[field]:03d}"
                set_nested_field(record, field, generated_value)
        else:
            # Simple field - use global counter
            if field not in dynamic_counters:
                dynamic_counters[field] = 1
            else:
                dynamic_counters[field] += 1
            
            generated_value = f"{processed_prefix}_{dynamic_counters[field]:03d}"
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
