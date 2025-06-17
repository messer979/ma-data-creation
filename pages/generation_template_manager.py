"""
Bulk Template Manager
Handles bulk export and import of all generation templates
"""

import json
import os
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from data_creation.template_generator import TemplateGenerator

from components.sidebar import render_sidebar


    
render_sidebar()

