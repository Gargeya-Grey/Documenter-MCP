"""Core orchestrator for the MCP Documentation Server."""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from ..config import ServerConfig, load_config
from ..logger import setup_logger, get_logger
from ..models import (
    ProjectAnalysisResult, FileAnalysisResult, 
    CodeElement, DocumentationIssue
)
from ..parsers.base import PythonParser
from ..analyzers.checker import DocumentationChecker
from ..analyzers.evaluator import DocumentationEvaluator
# Documentation generation functionality removed per project focus

logger = get_logger(__name__)


class DocumentationOrchestrator:
    """Orchestrates the documentation analysis and generation process."""
    
    def __init__(self, config_path: Optional[Path] = None):
        # Load configuration
        self.config = load_config(config_path)
        
        # Setup logging
        setup_logger(self.config.log_level, self.config.log_file)
        
        # Initialize components
        self.parser = PythonParser()
        self.checker = DocumentationChecker(self.config)
        self.evaluator = DocumentationEvaluator(self.config)
        # Documentation generation functionality removed per project focus
        
        logger.info(f"Documentation Orchestrator initialized for {self.config.name} v{self.config.version}")
    
    def analyze_project(self, project_path: Path) -> ProjectAnalysisResult:
        """Analyze an entire project for documentation issues."""
        logger.info(f"Starting analysis of project: {project_path}")
        
        start_time = datetime.now()
        
        # Create project result
        project_result = ProjectAnalysisResult(
            project_path=project_path
        )
        
        # Analyze each file
        files = self._get_files_to_analyze(project_path)
        logger.info(f"Found {len(files)} files to analyze")
        
        for file_path in files:
            try:
                file_result = self._analyze_file(file_path, project_path)
                if file_result:
                    project_result.files.append(file_result)
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")
                continue
        
        # Calculate project-level metrics
        self._calculate_project_metrics(project_result)
        
        # Evaluate project-wide consistency
        self.evaluator.evaluate_project(project_result)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Project analysis completed in {duration:.2f} seconds")
        
        return project_result
    
    # Documentation generation functionality removed per project focus
    
    def _get_files_to_analyze(self, project_path: Path) -> List[Path]:
        """Get list of files to analyze, respecting exclude patterns."""
        files = []
        
        # Convert exclude patterns to set for faster lookup
        exclude_patterns = set(self.config.exclude_patterns)
        
        for root, dirs, filenames in os.walk(project_path):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(root, d), exclude_patterns)]
            
            for filename in filenames:
                file_path = Path(root) / filename
                
                # Skip excluded files
                if self._should_exclude(str(file_path), exclude_patterns):
                    continue
                
                # Skip files that are too large
                try:
                    if file_path.stat().st_size > self.config.max_file_size_mb * 1024 * 1024:
                        logger.debug(f"Skipping large file: {file_path}")
                        continue
                except OSError:
                    pass
                
                # Check if parser can handle this file
                if self.parser.can_parse(file_path):
                    files.append(file_path)
        
        return files
    
    def _should_exclude(self, path: str, exclude_patterns: set) -> bool:
        """Check if a path should be excluded based on patterns."""
        path = Path(path)
        
        # Check exact matches
        if path.name in exclude_patterns:
            return True
        
        # Check extension matches
        if path.suffix in exclude_patterns:
            return True
        
        # Check path contains patterns
        path_str = str(path)
        return any(pattern in path_str for pattern in exclude_patterns if pattern.startswith('*'))
    
    def _analyze_file(self, file_path: Path, project_path: Path) -> Optional[FileAnalysisResult]:
        """Analyze a single file for documentation issues."""
        logger.debug(f"Analyzing file: {file_path}")
        
        try:
            # Determine language
            language = self._detect_language(file_path)
            if not language:
                logger.debug(f"Unsupported language for file: {file_path}")
                return None
            
            # Create file result
            file_result = FileAnalysisResult(
                file_path=file_path,
                language=language
            )
            
            # Parse file to extract elements
            elements = self.parser.parse_file(file_path)
            file_result.elements = elements
            
            # Check documentation
            self.checker.check_file(file_result)
            
            # Evaluate documentation quality
            self.evaluator.evaluate_file(file_result)
            
            logger.debug(f"Completed analysis of {file_path}: {len(elements)} elements, {len(file_result.issues)} issues")
            return file_result
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language based on file extension."""
        extension = file_path.suffix.lower()
        
        for lang, config in self.config.languages.items():
            if extension in config.extensions:
                return lang
        
        return None
    
    def _calculate_project_metrics(self, project_result: ProjectAnalysisResult) -> None:
        """Calculate project-level metrics from file results."""
        total_elements = 0
        documented_elements = 0
        issues_by_severity = {}
        coverage_by_language = {}
        
        # Aggregate metrics from files
        for file_result in project_result.files:
            total_elements += file_result.total_elements
            documented_elements += file_result.documented_elements
            
            # Count issues by severity
            for issue in file_result.issues:
                issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1
            
            # Track coverage by language
            if file_result.language not in coverage_by_language:
                coverage_by_language[file_result.language] = []
            coverage_by_language[file_result.language].append(file_result.coverage_score)
        
        # Calculate overall coverage
        project_result.total_elements = total_elements
        project_result.documented_elements = documented_elements
        project_result.overall_coverage = (
            documented_elements / total_elements if total_elements > 0 else 1.0
        )
        
        # Calculate coverage by language
        for language, scores in coverage_by_language.items():
            project_result.coverage_by_language[language] = sum(scores) / len(scores)
        
        # Store issues summary
        project_result.issues_by_severity = issues_by_severity
        
        logger.info(f"Project metrics: {total_elements} elements, {documented_elements} documented, {project_result.overall_coverage:.1%} coverage")
