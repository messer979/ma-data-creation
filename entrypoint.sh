#!/bin/bash

# Default to running the Streamlit app if no command is provided
if [ $# -eq 0 ]; then
    exec streamlit run app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
else
    exec "$@"
fi
