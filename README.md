# MCP Documentation Server

This project implements an MCP (Model Coordination Protocol) server for automated code documentation analysis and checking. It focuses on identifying documentation issues in codebases across multiple programming languages without modifying source files.

## Features

- **Multi-language Support**: Works with Python, JavaScript/TypeScript, Java, C++, Go, and more
- **Documentation Checking**: Verifies presence, format, and completeness of documentation
- **Documentation Evaluation**: Assesses clarity, consistency, and synchronization with code
- **MCP Integration**: Works as an MCP server for integration with other tools

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
# Analyze a project for documentation issues
python -m src.server analyze /path/to/project

# Check documentation without making changes
python -m src.server check /path/to/project
```

### As an MCP Server

```bash
# Run as MCP server
python -m src.server --mcp
```

## Configuration

The server can be configured using a YAML or TOML configuration file. See `config.example.yaml` for an example configuration.

## Project Structure

```
src/
├── cli.py              # Command-line interface
├── server.py           # Main MCP server implementation
├── config.py           # Configuration management
├── logger.py           # Logging setup
├── models.py           # Data models
├── core/
│   └── orchestrator.py # Core orchestration logic
├── parsers/
│   ├── base.py         # Base parser and Python parser
│   └── __init__.py
├── analyzers/
│   ├── checker.py      # Documentation checking
│   ├── evaluator.py    # Documentation evaluation
│   └── __init__.py
└── generators/
    └── __init__.py
```

## Development

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
