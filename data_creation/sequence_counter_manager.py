"""
Sequence Counter Manager
Manages persistent sequence counters across generation requests
"""

import streamlit as st
from typing import Dict, Any, Optional
from threading import Lock


class SequenceCounterManager:
    """
    Manages sequence counters that persist across generation requests.
    Works with both Streamlit (session_state) and standalone API (in-memory dict).
    """
    
    def __init__(self, use_streamlit: bool = True):
        """
        Initialize the sequence counter manager
        
        Args:
            use_streamlit: If True, use Streamlit session_state. If False, use in-memory dict (for API)
        """
        self.use_streamlit = use_streamlit
        self.session_key = "sequence_counters"
        self.enabled_key = "sequence_counters_enabled"
        
        # For API mode (non-Streamlit), use a thread-safe in-memory store
        if not use_streamlit:
            self._counters: Dict[str, int] = {}
            self._enabled = True  # Default to enabled for API
            self._lock = Lock()
    
    def is_enabled(self) -> bool:
        """Check if persistent sequence counters are enabled"""
        if self.use_streamlit:
            return st.session_state.get(self.enabled_key, False)
        else:
            return self._enabled
    
    def set_enabled(self, enabled: bool):
        """Enable or disable persistent sequence counters"""
        if self.use_streamlit:
            st.session_state[self.enabled_key] = enabled
        else:
            self._enabled = enabled
    
    def _get_counter_key(self, template_name: str, field_name: str) -> str:
        """Generate a unique key for a template+field combination"""
        return f"{template_name}::{field_name}"
    
    def get_counter(self, template_name: str, field_name: str) -> Optional[int]:
        """
        Get the current counter value for a template+field combination
        
        Args:
            template_name: Name of the generation template
            field_name: Name of the sequence field
            
        Returns:
            Current counter value, or None if not set
        """
        if not self.is_enabled():
            return None
        
        key = self._get_counter_key(template_name, field_name)
        
        if self.use_streamlit:
            counters = st.session_state.get(self.session_key, {})
            return counters.get(key)
        else:
            with self._lock:
                return self._counters.get(key)
    
    def set_counter(self, template_name: str, field_name: str, value: int):
        """
        Set the counter value for a template+field combination
        
        Args:
            template_name: Name of the generation template
            field_name: Name of the sequence field
            value: Counter value to set
        """
        if not self.is_enabled():
            return
        
        key = self._get_counter_key(template_name, field_name)
        
        if self.use_streamlit:
            if self.session_key not in st.session_state:
                st.session_state[self.session_key] = {}
            st.session_state[self.session_key][key] = value
        else:
            with self._lock:
                self._counters[key] = value
    
    def increment_counter(self, template_name: str, field_name: str) -> int:
        """
        Increment and return the counter value for a template+field combination
        
        Args:
            template_name: Name of the generation template
            field_name: Name of the sequence field
            
        Returns:
            The incremented counter value
        """
        if not self.is_enabled():
            return 1  # Return default if disabled
        
        key = self._get_counter_key(template_name, field_name)
        
        if self.use_streamlit:
            if self.session_key not in st.session_state:
                st.session_state[self.session_key] = {}
            
            if key not in st.session_state[self.session_key]:
                st.session_state[self.session_key][key] = 0
            
            st.session_state[self.session_key][key] += 1
            return st.session_state[self.session_key][key]
        else:
            with self._lock:
                if key not in self._counters:
                    self._counters[key] = 0
                self._counters[key] += 1
                return self._counters[key]
    
    def get_all_counters(self, template_name: Optional[str] = None) -> Dict[str, int]:
        """
        Get all counter values, optionally filtered by template name
        
        Args:
            template_name: Optional template name to filter by
            
        Returns:
            Dictionary of counter keys to values
        """
        if not self.is_enabled():
            return {}
        
        if self.use_streamlit:
            counters = st.session_state.get(self.session_key, {})
        else:
            with self._lock:
                counters = self._counters.copy()
        
        if template_name:
            # Filter by template name
            prefix = f"{template_name}::"
            return {k: v for k, v in counters.items() if k.startswith(prefix)}
        
        return counters
    
    def get_template_counters(self, template_name: str) -> Dict[str, int]:
        """
        Get all counters for a specific template, with field names as keys
        
        Args:
            template_name: Name of the generation template
            
        Returns:
            Dictionary mapping field names to counter values
        """
        all_counters = self.get_all_counters(template_name)
        prefix = f"{template_name}::"
        
        result = {}
        for key, value in all_counters.items():
            if key.startswith(prefix):
                field_name = key[len(prefix):]
                result[field_name] = value
        
        return result
    
    def reset_counters(self, template_name: Optional[str] = None):
        """
        Reset counters, optionally for a specific template only
        
        Args:
            template_name: Optional template name. If provided, only reset counters for that template.
                          If None, reset all counters.
        """
        if self.use_streamlit:
            if self.session_key not in st.session_state:
                return
            
            if template_name:
                # Reset only counters for this template
                prefix = f"{template_name}::"
                keys_to_remove = [k for k in st.session_state[self.session_key].keys() if k.startswith(prefix)]
                for key in keys_to_remove:
                    del st.session_state[self.session_key][key]
            else:
                # Reset all counters
                st.session_state[self.session_key] = {}
        else:
            with self._lock:
                if template_name:
                    # Reset only counters for this template
                    prefix = f"{template_name}::"
                    keys_to_remove = [k for k in self._counters.keys() if k.startswith(prefix)]
                    for key in keys_to_remove:
                        del self._counters[key]
                else:
                    # Reset all counters
                    self._counters.clear()
    
    def get_next_counter(self, template_name: str, field_name: str) -> int:
        """
        Get the next counter value (current + 1) without incrementing.
        Useful for displaying what the next value will be.
        
        Args:
            template_name: Name of the generation template
            field_name: Name of the sequence field
            
        Returns:
            The next counter value that will be used
        """
        current = self.get_counter(template_name, field_name)
        if current is None:
            return 1
        return current + 1
