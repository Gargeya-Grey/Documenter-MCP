"""Base classes for code parsers."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
import ast
import re

from ..models import CodeElement, CodeElementType, Parameter, ReturnInfo, ExceptionInfo
from ..logger import get_logger

logger = get_logger(__name__)


class BaseParser(ABC):
    """Abstract base class for language-specific code parsers."""
    
    def __init__(self, language: str, extensions: List[str]):
        self.language = language
        self.extensions = extensions
    
    @abstractmethod
    def parse_file(self, file_path: Path) -> List[CodeElement]:
        """Parse a file and extract code elements."""
        pass
    
    @abstractmethod
    def extract_docstring(self, node: Any) -> Optional[str]:
        """Extract docstring from a code node."""
        pass
    
    @abstractmethod
    def get_element_signature(self, element: CodeElement) -> str:
        """Get the signature string for a code element."""
        pass
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.extensions
    
    def _clean_docstring(self, docstring: str) -> str:
        """Clean and normalize docstring content."""
        if not docstring:
            return ""
        
        # Remove leading/trailing whitespace
        docstring = docstring.strip()
        
        # Remove common indentation
        lines = docstring.split('\n')
        if len(lines) > 1:
            # Find minimum indentation (excluding first line and empty lines)
            min_indent = float('inf')
            for line in lines[1:]:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, indent)
            
            # Remove common indentation
            if min_indent != float('inf'):
                lines = [lines[0]] + [line[min_indent:] if len(line) > min_indent else line 
                                     for line in lines[1:]]
                docstring = '\n'.join(lines)
        
        return docstring
    
    def _parse_docstring_sections(self, docstring: str) -> Dict[str, str]:
        """Parse docstring into sections (summary, description, parameters, etc.)."""
        if not docstring:
            return {}
        
        sections = {}
        lines = docstring.split('\n')
        current_section = 'summary'
        current_content = []
        
        section_patterns = {
            'args': r'^(Args|Arguments|Parameters):\s*$',
            'returns': r'^(Returns?|Return):\s*$',
            'raises': r'^(Raises?|Exceptions?):\s*$',
            'yields': r'^(Yields?):\s*$',
            'examples': r'^(Examples?):\s*$',
            'note': r'^(Note|Notes):\s*$',
            'warning': r'^(Warning|Warnings):\s*$',
        }
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line starts a new section
            section_found = None
            for section_name, pattern in section_patterns.items():
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    section_found = section_name
                    break
            
            if section_found:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = section_found
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections


class PythonParser(BaseParser):
    """Parser for Python code using AST."""
    
    def __init__(self):
        super().__init__("python", [".py"])
    
    def parse_file(self, file_path: Path) -> List[CodeElement]:
        """Parse a Python file and extract code elements."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            elements = []
            
            # Create module element
            module_element = CodeElement(
                name=file_path.stem,
                element_type=CodeElementType.MODULE,
                file_path=file_path,
                line_number=1,
                docstring=self.extract_docstring(tree)
            )
            
            # Parse module-level elements
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_element = self._parse_function(node, file_path)
                    if func_element:
                        elements.append(func_element)
                        module_element.functions.append(func_element)
                
                elif isinstance(node, ast.ClassDef):
                    class_element = self._parse_class(node, file_path)
                    if class_element:
                        elements.append(class_element)
                        module_element.classes.append(class_element)
            
            elements.insert(0, module_element)
            return elements
            
        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")
            return []
    
    def extract_docstring(self, node: ast.AST) -> Optional[str]:
        """Extract docstring from an AST node."""
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and 
                isinstance(node.body[0], ast.Expr) and 
                isinstance(node.body[0].value, ast.Constant) and 
                isinstance(node.body[0].value.value, str)):
                return self._clean_docstring(node.body[0].value.value)
        return None
    
    def get_element_signature(self, element: CodeElement) -> str:
        """Get the signature string for a Python code element."""
        if element.element_type == CodeElementType.FUNCTION:
            params = []
            for param in element.parameters:
                param_str = param.name
                if param.type_hint:
                    param_str += f": {param.type_hint}"
                if param.default_value:
                    param_str += f" = {param.default_value}"
                params.append(param_str)
            
            signature = f"def {element.name}({', '.join(params)})"
            if element.return_info and element.return_info.type_hint:
                signature += f" -> {element.return_info.type_hint}"
            return signature
        
        elif element.element_type == CodeElementType.CLASS:
            return f"class {element.name}"
        
        return element.name
    
    def _extract_parameters(self, node: ast.FunctionDef) -> List[Parameter]:
        """Extract parameter information from a function definition."""
        parameters = []
        
        # Handle 'self' parameter for methods
        if isinstance(node, ast.FunctionDef) and node.args.args:
            first_arg = node.args.args[0] if node.args.args else None
            if first_arg and first_arg.arg == 'self' and self._is_method(node):
                # Skip 'self' parameter for methods
                args = node.args.args[1:]
            else:
                args = node.args.args
        else:
            args = node.args.args or []
        
        # Extract parameter names and type hints
        for arg in args:
            param = Parameter(
                name=arg.arg,
                type_hint=self._get_type_annotation(arg.annotation) if arg.annotation else None
            )
            parameters.append(param)
        
        # Handle default values
        defaults = node.args.defaults
        if defaults:
            # Defaults apply to the last len(defaults) parameters
            for i, default in enumerate(defaults):
                param_index = len(parameters) - len(defaults) + i
                if 0 <= param_index < len(parameters):
                    parameters[param_index].default_value = ast.unparse(default)
                    parameters[param_index].is_required = False
        
        return parameters
    
    def _parse_function(self, node: ast.FunctionDef, file_path: Path) -> Optional[CodeElement]:
        """Parse a function definition."""
        try:
            # Determine if it's a method (inside a class)
            element_type = CodeElementType.METHOD if self._is_method(node) else CodeElementType.FUNCTION
            
            # Extract parameters
            parameters = self._extract_parameters(node)
            
            # Extract return type
            return_info = None
            if node.returns:
                return_info = ReturnInfo(
                    type_hint=self._get_type_annotation(node.returns)
                )
            
            # Create code element
            element = CodeElement(
                name=node.name,
                element_type=element_type,
                file_path=file_path,
                line_number=node.lineno,
                parameters=parameters,
                return_info=return_info
            )
            
            # Extract docstring
            docstring = ast.get_docstring(node)
            if docstring:
                element.docstring = docstring
                # Extract summary and description
                lines = docstring.strip().split('\n')
                element.summary = lines[0] if lines else ""
                element.description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
            
            return element
        except Exception as e:
            logger.error(f"Error parsing function {node.name}: {e}")
            return None
    
    def _parse_class(self, node: ast.ClassDef, file_path: Path) -> Optional[CodeElement]:
        """Parse a class definition."""
        try:
            element = CodeElement(
                name=node.name,
                element_type=CodeElementType.CLASS,
                file_path=file_path,
                line_number=node.lineno,
                end_line_number=getattr(node, 'end_lineno', None),
                docstring=self.extract_docstring(node),
                visibility=self._get_visibility(node.name)
            )
            
            # Parse methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method = self._parse_function(item, file_path)
                    if method:
                        element.methods.append(method)
            
            # Parse docstring for additional information
            if element.docstring:
                self._parse_docstring_info(element)
            
            return element
            
        except Exception as e:
            logger.error(f"Error parsing class {node.name}: {e}")
            return None
    
    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function is a method (defined inside a class)."""
        # This is a simplified check - in a full implementation,
        # you'd need to track the AST context
        return hasattr(node, 'parent') and isinstance(getattr(node, 'parent'), ast.ClassDef)
    
    def _get_type_annotation(self, annotation: ast.AST) -> str:
        """Get string representation of type annotation."""
        try:
            return ast.unparse(annotation)
        except:
            return str(annotation)
    
    def _get_visibility(self, name: str) -> str:
        """Determine visibility based on naming convention."""
        if name.startswith('__') and name.endswith('__'):
            return "special"
        elif name.startswith('__'):
            return "private"
        elif name.startswith('_'):
            return "protected"
        else:
            return "public"
    
    def _parse_docstring_info(self, element: CodeElement) -> None:
        """Parse docstring to extract parameter descriptions, return info, etc."""
        if not element.docstring:
            return
        
        sections = self._parse_docstring_sections(element.docstring)
        
        # Extract summary and description
        if 'summary' in sections:
            lines = sections['summary'].split('\n')
            element.summary = lines[0].strip()
            if len(lines) > 1:
                element.description = '\n'.join(lines[1:]).strip()
        
        # Parse parameter descriptions
        if 'args' in sections and element.parameters:
            self._parse_parameter_descriptions(sections['args'], element.parameters)
        
        # Parse return information
        if 'returns' in sections and element.return_info:
            element.return_info.description = sections['returns'].strip()
        
        # Parse exceptions
        if 'raises' in sections:
            element.exceptions = self._parse_exceptions(sections['raises'])
    
    def _parse_parameter_descriptions(self, args_section: str, parameters: List[Parameter]) -> None:
        """Parse parameter descriptions from docstring args section."""
        lines = args_section.split('\n')
        current_param = None
        current_desc = []
        
        param_dict = {p.name: p for p in parameters}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new parameter
            match = re.match(r'^(\w+):\s*(.*)', line)
            if match:
                # Save previous parameter description
                if current_param and current_desc:
                    if current_param in param_dict:
                        param_dict[current_param].description = ' '.join(current_desc).strip()
                
                # Start new parameter
                current_param = match.group(1)
                current_desc = [match.group(2)] if match.group(2) else []
            else:
                # Continuation of current parameter description
                if current_param:
                    current_desc.append(line)
        
        # Save last parameter description
        if current_param and current_desc:
            if current_param in param_dict:
                param_dict[current_param].description = ' '.join(current_desc).strip()
    
    def _parse_exceptions(self, raises_section: str) -> List[ExceptionInfo]:
        """Parse exception information from docstring raises section."""
        exceptions = []
        lines = raises_section.split('\n')
        current_exception = None
        current_desc = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new exception
            match = re.match(r'^(\w+(?:\.\w+)*):\s*(.*)', line)
            if match:
                # Save previous exception
                if current_exception and current_desc:
                    exceptions.append(ExceptionInfo(
                        exception_type=current_exception,
                        description=' '.join(current_desc).strip()
                    ))
                
                # Start new exception
                current_exception = match.group(1)
                current_desc = [match.group(2)] if match.group(2) else []
            else:
                # Continuation of current exception description
                if current_exception:
                    current_desc.append(line)
        
        # Save last exception
        if current_exception and current_desc:
            exceptions.append(ExceptionInfo(
                exception_type=current_exception,
                description=' '.join(current_desc).strip()
            ))
        
        return exceptions
