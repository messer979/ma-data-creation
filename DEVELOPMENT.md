# Development Guide

## Getting Started

### Prerequisites
- Python 3.8+
- Git
- pip package manager

### Setup Development Environment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd data-creation-app
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

## Development Workflow

### Branching Strategy
- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature development branches
- `hotfix/*`: Critical bug fixes

### Commit Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Code Style Guidelines
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable and function names

## Architecture Overview

### Core Components

1. **`app.py`** - Main Streamlit application
   - Entry point and routing
   - Session state management
   - Theme configuration

2. **`data_generator.py`** - Data generation engine
   - Template loading and processing
   - Data generation logic
   - Variable substitution

3. **`config_manager.py`** - Configuration management
   - Session state persistence
   - Template configurations
   - Import/export functionality

4. **`ui_components.py`** - UI component library
   - Reusable Streamlit components
   - Form rendering
   - Results display

5. **`api_operations.py`** - API communication
   - HTTP request handling
   - Batch processing
   - Error handling

6. **`endpoint_config_ui.py`** - Endpoint configuration
   - Template-specific settings
   - Payload wrapping configuration
   - Real-time preview

### Data Flow

```
Template Selection → Configuration → Data Generation → API Sending → Results
```

1. User selects template type
2. System loads template configuration
3. Data generator creates records
4. API operations handle sending
5. Results are displayed to user

## Testing Strategy

### Test Types
- **Unit Tests**: Individual function testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Full workflow testing
- **UI Tests**: Streamlit component testing

### Running Tests
```bash
# Run all tests
python -m pytest testing/

# Run specific test category
python testing/test_payload_wrapping.py
python testing/test_ui_config_integration.py
python testing/test_end_to_end.py

# Run with coverage
python -m pytest testing/ --cov=.
```

### Test Structure
```
testing/
├── test_payload_wrapping.py      # Payload structure tests
├── test_ui_config_integration.py # UI configuration tests
├── test_end_to_end.py            # Full workflow tests
├── test_generation_template.py   # Template generation tests
└── ...
```

## Adding New Features

### Adding a New Template Type

1. **Create template file**
   ```bash
   # Add to templates/ directory
   templates/new_data_type.json
   ```

2. **Create generation template**
   ```bash
   # Add to generation_templates/ directory
   generation_templates/new_data_type.json
   ```

3. **Configure endpoint**
   ```json
   // Add to configuration.json
   "new_data_type": {
     "endpoint": "/api/new-data",
     "type": "xint",
     "dataWrapper": true
   }
   ```

4. **Test the implementation**
   ```bash
   python testing/test_generation_template.py
   ```

### Adding UI Components

1. **Create component function**
   ```python
   def render_new_component(data):
       """Render a new UI component"""
       with st.container():
           # Component implementation
           pass
   ```

2. **Add to ui_components.py**
3. **Import in app.py**
4. **Test in Streamlit app**

### Extending API Operations

1. **Add new operation function**
   ```python
   def new_api_operation(data, config):
       """New API operation"""
       # Implementation
       pass
   ```

2. **Update api_operations.py**
3. **Add error handling**
4. **Write integration tests**

## Configuration Management

### Configuration Hierarchy
1. **Default**: `configuration.json`
2. **User**: `user_config.json` (gitignored)
3. **Session**: Streamlit session state
4. **Runtime**: Form inputs

### Adding Configuration Options

1. **Update config_manager.py**
   ```python
   def get_new_setting(self):
       return self.get_config('new_setting', default_value)
   ```

2. **Add UI controls**
   ```python
   new_value = st.text_input("New Setting", value=current_value)
   ```

3. **Update save logic**
4. **Test configuration persistence**

## Debugging Tips

### Common Issues
- **Session state not persisting**: Check key naming
- **Template not loading**: Verify JSON syntax
- **API calls failing**: Check endpoint configuration
- **UI not updating**: Use `st.rerun()` appropriately

### Debug Tools
```python
# Debug session state
st.write("Session State:", dict(st.session_state))

# Debug configuration
st.json(config_manager.get_all_config())

# Debug templates
st.json(data_generator.templates)
```

### Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

## Performance Considerations

### Optimization Tips
- Cache expensive operations with `@st.cache_data`
- Use session state for persistence
- Implement batch processing for large datasets
- Optimize template loading

### Memory Management
- Clear session state when appropriate
- Limit batch sizes for API calls
- Use generators for large data sets

## Deployment

### Local Development
```bash
streamlit run app.py --server.port 8501
```

### Production Deployment
- Use environment variables for sensitive config
- Set up proper logging
- Configure resource limits
- Implement health checks

## Contributing

1. **Fork the repository**
2. **Create feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```
3. **Make changes with tests**
4. **Commit with proper message**
5. **Push and create PR**

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No sensitive data in code
- [ ] Error handling is implemented
- [ ] Performance impact considered

## Resources

### Documentation
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [JSON Schema](https://json-schema.org/)

### Tools
- [VS Code](https://code.visualstudio.com/) with Python extension
- [Postman](https://www.postman.com/) for API testing
- [Git](https://git-scm.com/) for version control

---

Happy coding! 🚀
