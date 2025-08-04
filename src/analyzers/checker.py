"""Documentation checker for presence, format, and completeness analysis."""

import re
from typing import List, Dict, Set, Optional
from pathlib import Path

from ..models import (
    CodeElement, DocumentationIssue, DocumentationStatus, 
    CodeElementType, FileAnalysisResult
)
from ..config import ServerConfig, AnalysisConfig
from ..logger import get_logger

logger = get_logger(__name__)


class DocumentationChecker:
    """Checks documentation for presence, format, and completeness."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.analysis_config = config.analysis
    
    def check_file(self, file_result: FileAnalysisResult) -> None:
        """Check all elements in a file for documentation issues."""
        for element in file_result.elements:
            self._check_element(element, file_result)
        
        # Calculate coverage
        self._calculate_coverage(file_result)
    
    def _check_element(self, element: CodeElement, file_result: FileAnalysisResult) -> None:
        """Check a single code element for documentation issues."""
        issues = []
        
        # Check presence
        if self.analysis_config.check_presence:
            presence_issues = self._check_presence(element)
            issues.extend(presence_issues)
        
        # Check format (only if documentation exists)
        if element.docstring and self.analysis_config.check_format:
            format_issues = self._check_format(element, file_result.language)
            issues.extend(format_issues)
        
        # Check completeness (only if documentation exists)
        if element.docstring and self.analysis_config.check_completeness:
            completeness_issues = self._check_completeness(element)
            issues.extend(completeness_issues)
        
        # Update element status and issues
        element.issues = [issue.message for issue in issues]
        element.status = self._determine_status(element, issues)
        
        # Add issues to file result
        file_result.issues.extend(issues)
    
    def _check_presence(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if documentation is present."""
        issues = []
        
        # Skip private elements if configured
        if not self.analysis_config.check_presence:
            return issues
        
        # Check if element should have documentation
        if self._should_have_documentation(element):
            if not element.docstring or not element.docstring.strip():
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="missing_documentation",
                    severity="high" if element.visibility == "public" else "medium",
                    message=f"{element.element_type.value.title()} '{element.name}' is missing documentation",
                    suggestion=f"Add a docstring to describe the purpose and usage of {element.name}",
                    line_number=element.line_number
                ))
        
        return issues
    
    def _check_format(self, element: CodeElement, language: str) -> List[DocumentationIssue]:
        """Check if documentation follows the expected format."""
        issues = []
        
        if not element.docstring:
            return issues
        
        # Get expected format for the language
        lang_config = self.config.languages.get(language)
        if not lang_config:
            return issues
        
        doc_format = lang_config.doc_format
        
        # Check format based on style
        if doc_format.style == "google":
            issues.extend(self._check_google_format(element))
        elif doc_format.style == "numpy":
            issues.extend(self._check_numpy_format(element))
        elif doc_format.style == "sphinx":
            issues.extend(self._check_sphinx_format(element))
        elif doc_format.style == "javadoc":
            issues.extend(self._check_javadoc_format(element))
        elif doc_format.style == "jsdoc":
            issues.extend(self._check_jsdoc_format(element))
        
        return issues
    
    def _check_completeness(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if documentation is complete."""
        issues = []
        
        if not element.docstring:
            return issues
        
        # Check for summary/description
        if not element.summary and not self._has_summary_in_docstring(element.docstring):
            issues.append(DocumentationIssue(
                element=element,
                issue_type="missing_summary",
                severity="medium",
                message=f"{element.element_type.value.title()} '{element.name}' lacks a summary description",
                suggestion="Add a brief summary describing what this element does",
                line_number=element.line_number
            ))
        
        # Check parameters documentation for functions/methods
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            issues.extend(self._check_parameters_documentation(element))
            issues.extend(self._check_return_documentation(element))
            issues.extend(self._check_exceptions_documentation(element))
        
        return issues
    
    def _check_google_format(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check Google-style docstring format."""
        issues = []
        docstring = element.docstring
        
        # Check for proper sections
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            if element.parameters and not re.search(r'\n\s*Args:', docstring):
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="format_violation",
                    severity="low",
                    message="Google-style docstring should have 'Args:' section for parameters",
                    suggestion="Add 'Args:' section to document parameters",
                    line_number=element.line_number
                ))
            
            if element.return_info and not re.search(r'\n\s*Returns:', docstring):
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="format_violation",
                    severity="low",
                    message="Google-style docstring should have 'Returns:' section",
                    suggestion="Add 'Returns:' section to document return value",
                    line_number=element.line_number
                ))
        
        return issues
    
    def _check_numpy_format(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check NumPy-style docstring format."""
        issues = []
        docstring = element.docstring
        
        # Check for proper sections with underlines
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            if element.parameters and not re.search(r'\n\s*Parameters\s*\n\s*-+', docstring):
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="format_violation",
                    severity="low",
                    message="NumPy-style docstring should have 'Parameters' section with underline",
                    suggestion="Add 'Parameters' section with dashes underline",
                    line_number=element.line_number
                ))
        
        return issues
    
    def _check_sphinx_format(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check Sphinx-style docstring format."""
        issues = []
        docstring = element.docstring
        
        # Check for proper :param: and :return: directives
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            for param in element.parameters:
                if not re.search(rf':param {param.name}:', docstring):
                    issues.append(DocumentationIssue(
                        element=element,
                        issue_type="format_violation",
                        severity="low",
                        message=f"Sphinx-style docstring missing ':param {param.name}:' directive",
                        suggestion=f"Add ':param {param.name}: description' directive",
                        line_number=element.line_number
                    ))
        
        return issues
    
    def _check_javadoc_format(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check Javadoc-style documentation format."""
        issues = []
        docstring = element.docstring
        
        # Check for proper @param and @return tags
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            for param in element.parameters:
                if not re.search(rf'@param {param.name}', docstring):
                    issues.append(DocumentationIssue(
                        element=element,
                        issue_type="format_violation",
                        severity="low",
                        message=f"Javadoc-style comment missing '@param {param.name}' tag",
                        suggestion=f"Add '@param {param.name} description' tag",
                        line_number=element.line_number
                    ))
        
        return issues
    
    def _check_jsdoc_format(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check JSDoc-style documentation format."""
        issues = []
        docstring = element.docstring
        
        # Check for proper @param and @returns tags
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            for param in element.parameters:
                if not re.search(rf'@param {{[^}}]*}} {param.name}', docstring):
                    issues.append(DocumentationIssue(
                        element=element,
                        issue_type="format_violation",
                        severity="low",
                        message=f"JSDoc-style comment missing '@param {{type}} {param.name}' tag",
                        suggestion=f"Add '@param {{type}} {param.name} description' tag",
                        line_number=element.line_number
                    ))
        
        return issues
    
    def _check_parameters_documentation(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if all parameters are documented."""
        issues = []
        
        # Get documented parameters from docstring
        documented_params = self._extract_documented_parameters(element.docstring)
        
        # Check each parameter
        for param in element.parameters:
            # Skip 'self' and 'cls' parameters
            if param.name in ['self', 'cls']:
                continue
            
            if param.name not in documented_params:
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="missing_parameter_doc",
                    severity="medium",
                    message=f"Parameter '{param.name}' is not documented",
                    suggestion=f"Add documentation for parameter '{param.name}'",
                    line_number=element.line_number
                ))
            elif not documented_params[param.name].strip():
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="empty_parameter_doc",
                    severity="low",
                    message=f"Parameter '{param.name}' has empty documentation",
                    suggestion=f"Add description for parameter '{param.name}'",
                    line_number=element.line_number
                ))
        
        return issues
    
    def _check_return_documentation(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if return value is documented."""
        issues = []
        
        # Skip if no return type hint or if function name suggests no return value
        if (not element.return_info or 
            element.name.startswith('__') or 
            element.name in ['main', 'setup', 'teardown']):
            return issues
        
        # Check if return value is documented
        if not self._has_return_documentation(element.docstring):
            issues.append(DocumentationIssue(
                element=element,
                issue_type="missing_return_doc",
                severity="medium",
                message="Return value is not documented",
                suggestion="Add documentation for the return value",
                line_number=element.line_number
            ))
        
        return issues
    
    def _check_exceptions_documentation(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if exceptions are documented."""
        issues = []
        
        # This is a simplified check - in a full implementation,
        # you'd analyze the function body for raised exceptions
        if element.exceptions:
            documented_exceptions = self._extract_documented_exceptions(element.docstring)
            
            for exception in element.exceptions:
                if exception.exception_type not in documented_exceptions:
                    issues.append(DocumentationIssue(
                        element=element,
                        issue_type="missing_exception_doc",
                        severity="low",
                        message=f"Exception '{exception.exception_type}' is not documented",
                        suggestion=f"Add documentation for exception '{exception.exception_type}'",
                        line_number=element.line_number
                    ))
        
        return issues
    
    def _should_have_documentation(self, element: CodeElement) -> bool:
        """Determine if an element should have documentation."""
        # Always document public elements
        if element.visibility == "public":
            return True
        
        # Document protected elements if configured
        if element.visibility == "protected":
            return True  # Could be configurable
        
        # Skip private elements unless specifically configured
        if element.visibility == "private":
            return False
        
        # Document special methods selectively
        if element.visibility == "special":
            # Document common special methods
            special_methods_to_document = {
                '__init__', '__str__', '__repr__', '__call__',
                '__enter__', '__exit__', '__iter__', '__next__'
            }
            return element.name in special_methods_to_document
        
        return True
    
    def _has_summary_in_docstring(self, docstring: str) -> bool:
        """Check if docstring has a summary (first line)."""
        if not docstring:
            return False
        
        first_line = docstring.split('\n')[0].strip()
        return len(first_line) > 0 and not first_line.startswith(('Args:', 'Parameters:', 'Returns:'))
    
    def _extract_documented_parameters(self, docstring: str) -> Dict[str, str]:
        """Extract documented parameters from docstring."""
        if not docstring:
            return {}
        
        documented = {}
        
        # Google style: Args:
        args_match = re.search(r'Args:\s*\n(.*?)(?=\n\s*\w+:|$)', docstring, re.DOTALL)
        if args_match:
            args_section = args_match.group(1)
            for match in re.finditer(r'(\w+):\s*(.*?)(?=\n\s*\w+:|$)', args_section, re.DOTALL):
                param_name = match.group(1)
                param_desc = match.group(2).strip()
                documented[param_name] = param_desc
        
        # Sphinx style: :param name:
        for match in re.finditer(r':param (\w+):\s*(.*?)(?=\n|$)', docstring):
            param_name = match.group(1)
            param_desc = match.group(2).strip()
            documented[param_name] = param_desc
        
        return documented
    
    def _has_return_documentation(self, docstring: str) -> bool:
        """Check if return value is documented."""
        if not docstring:
            return False
        
        # Check for various return documentation patterns
        patterns = [
            r'\n\s*Returns?:\s*\w+',
            r'\n\s*Return:\s*\w+',
            r':returns?:\s*\w+',
            r':return:\s*\w+',
            r'@returns?\s+\w+',
            r'@return\s+\w+'
        ]
        
        return any(re.search(pattern, docstring, re.IGNORECASE) for pattern in patterns)
    
    def _extract_documented_exceptions(self, docstring: str) -> Set[str]:
        """Extract documented exceptions from docstring."""
        if not docstring:
            return set()
        
        documented = set()
        
        # Google style: Raises:
        raises_match = re.search(r'Raises:\s*\n(.*?)(?=\n\s*\w+:|$)', docstring, re.DOTALL)
        if raises_match:
            raises_section = raises_match.group(1)
            for match in re.finditer(r'(\w+(?:\.\w+)*):', raises_section):
                documented.add(match.group(1))
        
        # Sphinx style: :raises Exception:
        for match in re.finditer(r':raises (\w+(?:\.\w+)*):', docstring):
            documented.add(match.group(1))
        
        return documented
    
    def _determine_status(self, element: CodeElement, issues: List[DocumentationIssue]) -> DocumentationStatus:
        """Determine the documentation status based on issues."""
        if not element.docstring:
            return DocumentationStatus.MISSING
        
        # Count issues by severity
        critical_issues = sum(1 for issue in issues if issue.severity == "critical")
        high_issues = sum(1 for issue in issues if issue.severity == "high")
        medium_issues = sum(1 for issue in issues if issue.severity == "medium")
        low_issues = sum(1 for issue in issues if issue.severity == "low")
        
        if critical_issues > 0:
            return DocumentationStatus.INCOMPLETE
        elif high_issues > 0:
            return DocumentationStatus.INCOMPLETE
        elif medium_issues > 2:
            return DocumentationStatus.INCOMPLETE
        elif medium_issues > 0 or low_issues > 3:
            return DocumentationStatus.OUTDATED
        elif low_issues > 0:
            return DocumentationStatus.GOOD
        else:
            return DocumentationStatus.EXCELLENT
    
    def _calculate_coverage(self, file_result: FileAnalysisResult) -> None:
        """Calculate documentation coverage for the file."""
        total_elements = 0
        documented_elements = 0
        
        for element in file_result.elements:
            if self._should_have_documentation(element):
                total_elements += 1
                if element.status != DocumentationStatus.MISSING:
                    documented_elements += 1
        
        file_result.total_elements = total_elements
        file_result.documented_elements = documented_elements
        file_result.coverage_score = (
            documented_elements / total_elements if total_elements > 0 else 1.0
        )
