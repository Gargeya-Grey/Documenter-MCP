"""Documentation evaluator for clarity, consistency, and synchronization analysis."""

import re
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import nltk
import textstat
from collections import Counter, defaultdict

from ..models import (
    CodeElement, DocumentationIssue, FileAnalysisResult, 
    ProjectAnalysisResult, CodeElementType
)
from ..config import ServerConfig
from ..logger import get_logger

logger = get_logger(__name__)


class DocumentationEvaluator:
    """Evaluates documentation quality, clarity, and consistency."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.analysis_config = config.analysis
        self._initialize_nlp()
        
        # Track terminology across project
        self.project_terminology: Dict[str, Set[str]] = defaultdict(set)
        self.project_patterns: Dict[str, int] = Counter()
    
    def _initialize_nlp(self):
        """Initialize NLP resources."""
        try:
            # Download required NLTK data if not present
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to initialize NLTK resources: {e}")
    
    def evaluate_file(self, file_result: FileAnalysisResult) -> None:
        """Evaluate all elements in a file for documentation quality."""
        for element in file_result.elements:
            if element.docstring:
                self._evaluate_element(element, file_result)
        
        # Check file-level consistency
        if self.analysis_config.evaluate_consistency:
            self._check_file_consistency(file_result)
    
    def evaluate_project(self, project_result: ProjectAnalysisResult) -> None:
        """Evaluate project-wide documentation consistency."""
        if not self.analysis_config.evaluate_consistency:
            return
        
        # Collect terminology from all files
        for file_result in project_result.files:
            self._collect_terminology(file_result)
        
        # Check cross-file consistency
        for file_result in project_result.files:
            consistency_issues = self._check_cross_file_consistency(file_result)
            file_result.issues.extend(consistency_issues)
    
    def _evaluate_element(self, element: CodeElement, file_result: FileAnalysisResult) -> None:
        """Evaluate a single code element's documentation."""
        issues = []
        
        # Evaluate clarity
        if self.analysis_config.evaluate_clarity:
            clarity_issues = self._evaluate_clarity(element)
            issues.extend(clarity_issues)
        
        # Check code-comment synchronization
        if self.analysis_config.check_sync:
            sync_issues = self._check_synchronization(element)
            issues.extend(sync_issues)
        
        # Add issues to element and file
        element.issues.extend([issue.message for issue in issues])
        file_result.issues.extend(issues)
    
    def _evaluate_clarity(self, element: CodeElement) -> List[DocumentationIssue]:
        """Evaluate documentation clarity and readability."""
        issues = []
        docstring = element.docstring
        
        if not docstring:
            return issues
        
        # Check readability metrics
        readability_issues = self._check_readability(element, docstring)
        issues.extend(readability_issues)
        
        # Check for common clarity problems
        clarity_issues = self._check_clarity_problems(element, docstring)
        issues.extend(clarity_issues)
        
        # Check grammar and spelling (simplified)
        grammar_issues = self._check_grammar_and_spelling(element, docstring)
        issues.extend(grammar_issues)
        
        return issues
    
    def _check_readability(self, element: CodeElement, docstring: str) -> List[DocumentationIssue]:
        """Check readability metrics for documentation."""
        issues = []
        
        try:
            # Calculate readability scores
            flesch_score = textstat.flesch_reading_ease(docstring)
            flesch_grade = textstat.flesch_kincaid_grade(docstring)
            
            # Flag if too difficult to read
            if flesch_score < 30:  # Very difficult
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="readability_poor",
                    severity="medium",
                    message=f"Documentation is very difficult to read (Flesch score: {flesch_score:.1f})",
                    suggestion="Simplify sentences and use clearer language",
                    line_number=element.line_number
                ))
            elif flesch_score < 50:  # Difficult
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="readability_difficult",
                    severity="low",
                    message=f"Documentation is difficult to read (Flesch score: {flesch_score:.1f})",
                    suggestion="Consider simplifying complex sentences",
                    line_number=element.line_number
                ))
            
            # Flag if grade level is too high
            if flesch_grade > 12:
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="readability_grade_high",
                    severity="low",
                    message=f"Documentation requires college-level reading (Grade: {flesch_grade:.1f})",
                    suggestion="Use simpler vocabulary and shorter sentences",
                    line_number=element.line_number
                ))
        
        except Exception as e:
            logger.debug(f"Error calculating readability for {element.name}: {e}")
        
        return issues
    
    def _check_clarity_problems(self, element: CodeElement, docstring: str) -> List[DocumentationIssue]:
        """Check for common clarity problems in documentation."""
        issues = []
        
        # Check for vague language
        vague_words = [
            'somehow', 'something', 'stuff', 'thing', 'things',
            'various', 'several', 'many', 'some', 'etc'
        ]
        
        for word in vague_words:
            if re.search(rf'\b{word}\b', docstring, re.IGNORECASE):
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="vague_language",
                    severity="low",
                    message=f"Documentation contains vague language: '{word}'",
                    suggestion=f"Replace '{word}' with more specific terms",
                    line_number=element.line_number
                ))
        
        # Check for overly long sentences
        sentences = re.split(r'[.!?]+', docstring)
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 25:  # Arbitrary threshold
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="sentence_too_long",
                    severity="low",
                    message="Documentation contains very long sentences",
                    suggestion="Break long sentences into shorter, clearer ones",
                    line_number=element.line_number
                ))
                break  # Only flag once per element
        
        # Check for passive voice (simplified detection)
        passive_indicators = ['is done', 'was done', 'are handled', 'were handled', 'is performed']
        for indicator in passive_indicators:
            if indicator in docstring.lower():
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="passive_voice",
                    severity="low",
                    message="Documentation uses passive voice",
                    suggestion="Use active voice for clearer communication",
                    line_number=element.line_number
                ))
                break
        
        # Check for missing articles (a, an, the) - simplified
        if len(docstring.split()) > 5:  # Only check substantial documentation
            article_ratio = len(re.findall(r'\b(a|an|the)\b', docstring, re.IGNORECASE)) / len(docstring.split())
            if article_ratio < 0.05:  # Very low article usage
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="missing_articles",
                    severity="low",
                    message="Documentation may be missing articles (a, an, the)",
                    suggestion="Review and add appropriate articles for better readability",
                    line_number=element.line_number
                ))
        
        return issues
    
    def _check_grammar_and_spelling(self, element: CodeElement, docstring: str) -> List[DocumentationIssue]:
        """Check for basic grammar and spelling issues."""
        issues = []
        
        # Check for common grammar mistakes
        grammar_patterns = [
            (r'\bit\'s\b.*\bpurpose\b', "Use 'its' instead of 'it's' for possession"),
            (r'\byour\b.*\bwelcome\b', "Use 'you're' instead of 'your' before 'welcome'"),
            (r'\baffect\b.*\bresult\b', "Consider 'effect' instead of 'affect' as a noun"),
            (r'\bthen\b.*\bcomparison\b', "Use 'than' for comparisons, not 'then'"),
        ]
        
        for pattern, suggestion in grammar_patterns:
            if re.search(pattern, docstring, re.IGNORECASE):
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="grammar_error",
                    severity="low",
                    message="Possible grammar error detected",
                    suggestion=suggestion,
                    line_number=element.line_number
                ))
        
        # Check for repeated words
        words = docstring.lower().split()
        for i in range(len(words) - 1):
            if words[i] == words[i + 1] and len(words[i]) > 2:
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="repeated_word",
                    severity="low",
                    message=f"Repeated word detected: '{words[i]}'",
                    suggestion="Remove duplicate words",
                    line_number=element.line_number
                ))
                break  # Only flag once per element
        
        return issues
    
    def _check_synchronization(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if documentation is synchronized with code."""
        issues = []
        
        if not element.docstring:
            return issues
        
        # Check parameter synchronization
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            sync_issues = self._check_parameter_sync(element)
            issues.extend(sync_issues)
        
        # Check for outdated information (heuristic-based)
        outdated_issues = self._check_outdated_information(element)
        issues.extend(outdated_issues)
        
        return issues
    
    def _check_parameter_sync(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if documented parameters match actual parameters."""
        issues = []
        
        # Get documented parameters
        documented_params = self._extract_documented_parameters(element.docstring)
        actual_params = {p.name for p in element.parameters if p.name not in ['self', 'cls']}
        
        # Check for documented parameters that don't exist in code
        for doc_param in documented_params:
            if doc_param not in actual_params:
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="sync_extra_param",
                    severity="medium",
                    message=f"Documented parameter '{doc_param}' not found in function signature",
                    suggestion=f"Remove documentation for '{doc_param}' or check function signature",
                    line_number=element.line_number
                ))
        
        # Check for actual parameters not documented
        for actual_param in actual_params:
            if actual_param not in documented_params:
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="sync_missing_param",
                    severity="medium",
                    message=f"Parameter '{actual_param}' exists in code but not documented",
                    suggestion=f"Add documentation for parameter '{actual_param}'",
                    line_number=element.line_number
                ))
        
        return issues
    
    def _check_outdated_information(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check for potentially outdated information in documentation."""
        issues = []
        docstring = element.docstring.lower()
        
        # Look for temporal indicators that might be outdated
        temporal_indicators = [
            'currently', 'now', 'at the moment', 'for now',
            'temporary', 'temporarily', 'will be', 'todo', 'fixme'
        ]
        
        for indicator in temporal_indicators:
            if indicator in docstring:
                issues.append(DocumentationIssue(
                    element=element,
                    issue_type="potentially_outdated",
                    severity="low",
                    message=f"Documentation contains temporal language: '{indicator}'",
                    suggestion="Review and update temporal references in documentation",
                    line_number=element.line_number
                ))
                break  # Only flag once per element
        
        return issues
    
    def _check_file_consistency(self, file_result: FileAnalysisResult) -> None:
        """Check consistency within a single file."""
        # Collect documentation styles used in the file
        styles = self._analyze_documentation_styles(file_result.elements)
        
        # Flag if multiple styles are used inconsistently
        if len(styles) > 1:
            # Create issue for inconsistent styles
            for element in file_result.elements:
                if element.docstring:
                    file_result.issues.append(DocumentationIssue(
                        element=element,
                        issue_type="inconsistent_style",
                        severity="low",
                        message=f"File uses multiple documentation styles: {', '.join(styles)}",
                        suggestion="Use consistent documentation style throughout the file",
                        line_number=element.line_number
                    ))
                    break  # Only add once per file
    
    def _collect_terminology(self, file_result: FileAnalysisResult) -> None:
        """Collect terminology used in documentation for consistency checking."""
        for element in file_result.elements:
            if element.docstring:
                # Extract technical terms (simplified)
                words = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', element.docstring)
                for word in words:
                    self.project_terminology[word.lower()].add(word)
                
                # Track common patterns
                if element.summary:
                    pattern = self._extract_summary_pattern(element.summary)
                    if pattern:
                        self.project_patterns[pattern] += 1
    
    def _check_cross_file_consistency(self, file_result: FileAnalysisResult) -> List[DocumentationIssue]:
        """Check consistency across files in the project."""
        issues = []
        
        # Check terminology consistency
        for element in file_result.elements:
            if element.docstring:
                terminology_issues = self._check_terminology_consistency(element)
                issues.extend(terminology_issues)
        
        return issues
    
    def _check_terminology_consistency(self, element: CodeElement) -> List[DocumentationIssue]:
        """Check if terminology is used consistently across the project."""
        issues = []
        
        # Find terms that have multiple capitalizations
        for term_lower, variations in self.project_terminology.items():
            if len(variations) > 1:
                for variation in variations:
                    if variation in element.docstring:
                        most_common = max(variations, key=lambda x: self.project_terminology[term_lower])
                        if variation != most_common:
                            issues.append(DocumentationIssue(
                                element=element,
                                issue_type="terminology_inconsistency",
                                severity="low",
                                message=f"Inconsistent terminology: '{variation}' vs '{most_common}'",
                                suggestion=f"Use consistent terminology: '{most_common}'",
                                line_number=element.line_number
                            ))
        
        return issues
    
    def _analyze_documentation_styles(self, elements: List[CodeElement]) -> Set[str]:
        """Analyze what documentation styles are used in elements."""
        styles = set()
        
        for element in elements:
            if element.docstring:
                docstring = element.docstring
                
                # Detect Google style
                if re.search(r'\n\s*Args:\s*\n', docstring):
                    styles.add("google")
                
                # Detect NumPy style
                if re.search(r'\n\s*Parameters\s*\n\s*-+', docstring):
                    styles.add("numpy")
                
                # Detect Sphinx style
                if re.search(r':param \w+:', docstring):
                    styles.add("sphinx")
                
                # Detect Javadoc style
                if re.search(r'@param \w+', docstring):
                    styles.add("javadoc")
                
                # Detect JSDoc style
                if re.search(r'@param \{[^}]*\} \w+', docstring):
                    styles.add("jsdoc")
        
        return styles
    
    def _extract_summary_pattern(self, summary: str) -> Optional[str]:
        """Extract pattern from summary for consistency checking."""
        # Simplified pattern extraction
        words = summary.lower().split()
        if len(words) >= 2:
            # Look for verb patterns
            if words[0] in ['returns', 'gets', 'sets', 'creates', 'deletes', 'updates']:
                return f"{words[0]}_pattern"
            elif words[0] in ['a', 'an', 'the'] and len(words) >= 3:
                return f"{words[1]}_pattern"
        
        return None
    
    def _extract_documented_parameters(self, docstring: str) -> Set[str]:
        """Extract parameter names that are documented."""
        if not docstring:
            return set()
        
        documented = set()
        
        # Google style: Args:
        args_match = re.search(r'Args:\s*\n(.*?)(?=\n\s*\w+:|$)', docstring, re.DOTALL)
        if args_match:
            args_section = args_match.group(1)
            for match in re.finditer(r'(\w+):', args_section):
                documented.add(match.group(1))
        
        # Sphinx style: :param name:
        for match in re.finditer(r':param (\w+):', docstring):
            documented.add(match.group(1))
        
        # Javadoc style: @param name
        for match in re.finditer(r'@param (\w+)', docstring):
            documented.add(match.group(1))
        
        # JSDoc style: @param {type} name
        for match in re.finditer(r'@param \{[^}]*\} (\w+)', docstring):
            documented.add(match.group(1))
        
        return documented
