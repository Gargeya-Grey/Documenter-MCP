"""Data models for the MCP Documentation Server."""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class DocumentationStatus(Enum):
    """Status of documentation for a code element."""
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    OUTDATED = "outdated"
    GOOD = "good"
    EXCELLENT = "excellent"


class CodeElementType(Enum):
    """Types of code elements that can be documented."""
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"
    VARIABLE = "variable"
    CONSTANT = "constant"
    PROPERTY = "property"


@dataclass
class Parameter:
    """Represents a function/method parameter."""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    description: Optional[str] = None
    is_required: bool = True


@dataclass
class ReturnInfo:
    """Represents return information for a function/method."""
    type_hint: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ExceptionInfo:
    """Represents exception information for a function/method."""
    exception_type: str
    description: Optional[str] = None
    conditions: Optional[str] = None


@dataclass
class CodeElement:
    """Represents a code element (function, class, method, etc.)."""
    name: str
    element_type: CodeElementType
    file_path: Path
    line_number: int
    end_line_number: Optional[int] = None
    
    # Documentation content
    docstring: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    
    # Function/Method specific
    parameters: List[Parameter] = field(default_factory=list)
    return_info: Optional[ReturnInfo] = None
    exceptions: List[ExceptionInfo] = field(default_factory=list)
    
    # Class specific
    attributes: List['CodeElement'] = field(default_factory=list)
    methods: List['CodeElement'] = field(default_factory=list)
    
    # Module specific
    classes: List['CodeElement'] = field(default_factory=list)
    functions: List['CodeElement'] = field(default_factory=list)
    
    # Analysis results
    status: DocumentationStatus = DocumentationStatus.MISSING
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    # Metadata
    complexity_score: Optional[float] = None
    visibility: str = "public"  # public, private, protected
    is_deprecated: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class DocumentationIssue:
    """Represents a documentation issue found during analysis."""
    element: CodeElement
    issue_type: str
    severity: str  # low, medium, high, critical
    message: str
    suggestion: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class FileAnalysisResult:
    """Results of analyzing a single file."""
    file_path: Path
    language: str
    elements: List[CodeElement] = field(default_factory=list)
    issues: List[DocumentationIssue] = field(default_factory=list)
    coverage_score: float = 0.0
    total_elements: int = 0
    documented_elements: int = 0
    
    # File metadata
    lines_of_code: int = 0
    complexity_score: Optional[float] = None
    last_modified: Optional[str] = None


@dataclass
class ProjectAnalysisResult:
    """Results of analyzing an entire project."""
    project_path: Path
    files: List[FileAnalysisResult] = field(default_factory=list)
    overall_coverage: float = 0.0
    total_elements: int = 0
    documented_elements: int = 0
    
    # Summary statistics
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    coverage_by_language: Dict[str, float] = field(default_factory=dict)
    coverage_by_file_type: Dict[str, float] = field(default_factory=dict)
    
    # Generated documentation
    master_doc_path: Optional[Path] = None
    generated_files: List[Path] = field(default_factory=list)


@dataclass
class GeneratedDocumentation:
    """Represents generated documentation for a code element."""
    element: CodeElement
    content: str
    format_type: str  # markdown, html, rst, etc.
    confidence_score: float = 0.0
    generation_method: str = "ai"  # ai, template, manual
    
    # Quality metrics
    readability_score: Optional[float] = None
    completeness_score: Optional[float] = None
    consistency_score: Optional[float] = None


@dataclass
class MasterDocumentSection:
    """Represents a section in the master documentation."""
    title: str
    content: str
    level: int = 1
    anchor_id: Optional[str] = None
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    subsections: List['MasterDocumentSection'] = field(default_factory=list)


@dataclass
class MasterDocument:
    """Represents the complete master documentation."""
    title: str
    project_path: Path
    sections: List[MasterDocumentSection] = field(default_factory=list)
    table_of_contents: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    generated_at: Optional[str] = None
    generator_version: Optional[str] = None
    total_files: int = 0
    total_elements: int = 0
    
    # Cross-references
    cross_references: Dict[str, List[str]] = field(default_factory=dict)
    external_links: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class AnalysisConfig:
    """Configuration for code analysis."""
    include_private: bool = False
    include_tests: bool = True
    min_function_length: int = 1
    max_complexity_threshold: int = 10
    required_sections: List[str] = field(default_factory=lambda: [
        "summary", "parameters", "returns"
    ])


@dataclass
class GenerationConfig:
    """Configuration for documentation generation."""
    style: str = "google"
    include_examples: bool = True
    include_type_hints: bool = True
    max_line_length: int = 79
    generate_toc: bool = True
    include_source_links: bool = True
