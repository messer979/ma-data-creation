def scrub_order_data(order_data: list, to_headers) -> list:
    """
    Scrub order data to ensure it is in the correct format.
    
    Args:
        order_data (list): List of order data dictionaries.
        
    Returns:
        list: Scrubbed order data.
    """
    for order in order_data:
        order['OriginFacilityId'] = to_headers['SelectedLocation'] 
        order['MinimumStatus'] = 1000
        order['MaximumStatus'] = 1000
    return order_data


