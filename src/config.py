"""Configuration management for the MCP Documentation Server."""

from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field
import yaml
import toml


class DocumentationFormat(BaseModel):
    """Configuration for documentation formats."""
    name: str
    style: str = "google"  # google, numpy, sphinx, javadoc, jsdoc
    include_types: bool = True
    include_examples: bool = True
    max_line_length: int = 79


class LanguageConfig(BaseModel):
    """Configuration for programming language support."""
    name: str
    extensions: List[str]
    parser: str
    doc_format: DocumentationFormat
    comment_styles: List[str] = Field(default_factory=list)


class OutputConfig(BaseModel):
    """Configuration for output generation."""
    formats: List[str] = Field(default=["markdown", "html"])
    output_dir: str = "docs"
    master_file_name: str = "documentation"
    include_toc: bool = True
    include_search: bool = True
    theme: str = "default"


class AnalysisConfig(BaseModel):
    """Configuration for code analysis."""
    check_presence: bool = True
    check_format: bool = True
    check_completeness: bool = True
    evaluate_clarity: bool = True
    evaluate_consistency: bool = True
    check_sync: bool = True
    min_coverage_threshold: float = 0.8


class ServerConfig(BaseModel):
    """Main configuration for the MCP Documentation Server."""
    
    # Server settings
    name: str = "documenter-mcp"
    version: str = "1.0.0"
    
    # Language configurations
    languages: Dict[str, LanguageConfig] = Field(default_factory=dict)
    
    # Analysis settings
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    
    # Output settings
    output: OutputConfig = Field(default_factory=OutputConfig)
    
    # File processing
    exclude_patterns: List[str] = Field(default_factory=lambda: [
        "*.pyc", "__pycache__", ".git", "node_modules", "venv", ".env"
    ])
    max_file_size_mb: int = 10
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None


def get_default_config() -> ServerConfig:
    """Get default configuration with built-in language support."""
    
    python_config = LanguageConfig(
        name="python",
        extensions=[".py"],
        parser="tree-sitter-python",
        doc_format=DocumentationFormat(
            name="google",
            style="google",
            include_types=True,
            include_examples=True
        ),
        comment_styles=["#", '"""', "'''"]
    )
    
    javascript_config = LanguageConfig(
        name="javascript",
        extensions=[".js", ".ts", ".jsx", ".tsx"],
        parser="tree-sitter-javascript",
        doc_format=DocumentationFormat(
            name="jsdoc",
            style="jsdoc",
            include_types=True,
            include_examples=True
        ),
        comment_styles=["//", "/*", "/**"]
    )
    
    java_config = LanguageConfig(
        name="java",
        extensions=[".java"],
        parser="tree-sitter-java",
        doc_format=DocumentationFormat(
            name="javadoc",
            style="javadoc",
            include_types=True,
            include_examples=True
        ),
        comment_styles=["//", "/*", "/**"]
    )
    
    cpp_config = LanguageConfig(
        name="cpp",
        extensions=[".cpp", ".cc", ".cxx", ".h", ".hpp"],
        parser="tree-sitter-cpp",
        doc_format=DocumentationFormat(
            name="doxygen",
            style="doxygen",
            include_types=True,
            include_examples=True
        ),
        comment_styles=["//", "/*", "/**"]
    )
    
    go_config = LanguageConfig(
        name="go",
        extensions=[".go"],
        parser="tree-sitter-go",
        doc_format=DocumentationFormat(
            name="godoc",
            style="godoc",
            include_types=True,
            include_examples=True
        ),
        comment_styles=["//", "/*"]
    )
    
    return ServerConfig(
        languages={
            "python": python_config,
            "javascript": javascript_config,
            "java": java_config,
            "cpp": cpp_config,
            "go": go_config
        }
    )


def load_config(config_path: Optional[Path] = None) -> ServerConfig:
    """Load configuration from file or return default."""
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                    data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.toml':
                    data = toml.load(f)
                else:
                    raise ValueError(f"Unsupported config format: {config_path.suffix}")
            
            return ServerConfig(**data)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            print("Using default configuration.")
    
    return get_default_config()


def save_config(config: ServerConfig, config_path: Path) -> None:
    """Save configuration to file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            yaml.dump(config.model_dump(), f, default_flow_style=False, indent=2)
        elif config_path.suffix.lower() == '.toml':
            toml.dump(config.model_dump(), f)
        else:
            raise ValueError(f"Unsupported config format: {config_path.suffix}")
