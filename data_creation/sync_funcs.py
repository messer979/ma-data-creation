def get_failed_count(res_save) -> int:
    """
    Get the count of failed items from the response.
    
    Args:
        res_save (Response): The response object from the bulk import request.
        
    Returns:
        int: Count of failed items.
    """
    if res_save.status_code == 200:
        return res_save.json()['data'].get('FailedCount', 'N/A')
    return 'N/A'