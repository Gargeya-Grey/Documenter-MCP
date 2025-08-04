"""Main entry point for the MCP Documentation Server."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP

from .core.orchestrator import DocumentationOrchestrator
from .config import load_config
from .logger import setup_logger, get_logger

logger = get_logger(__name__)


class DocumentationMCPServer:
    """MCP Server implementation for documentation analysis and checking."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.config = load_config(config_path)
        setup_logger(self.config.log_level, self.config.log_file)
        
        # Initialize orchestrator
        self.orchestrator = DocumentationOrchestrator(config_path)
        
        # Initialize MCP server
        self.server = FastMCP("documenter-mcp")
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _register_tools(self):
        """Register MCP tools."""
        @self.server.tool()
        def analyze_project(project_path: str) -> Dict[str, Any]:
            """Analyze a project for documentation issues.
            
            Args:
                project_path: Path to the project directory
            
            Returns:
                Analysis results including coverage and issues
            """
            try:
                project_path_obj = Path(project_path).resolve()
                result = self.orchestrator.analyze_project(project_path_obj)
                
                # Convert to JSON-serializable format
                return {
                    "project_path": str(result.project_path),
                    "total_elements": result.total_elements,
                    "documented_elements": result.documented_elements,
                    "overall_coverage": result.overall_coverage,
                    "issues_by_severity": result.issues_by_severity,
                    "coverage_by_language": result.coverage_by_language
                }
            except Exception as e:
                logger.error(f"Error in analyze_project: {e}")
                return {"error": str(e)}
        
        @self.server.tool()
        def check_documentation(project_path: str) -> Dict[str, Any]:
            """Check documentation without making changes.
            
            Args:
                project_path: Path to the project directory
            
            Returns:
                Check results including issues found
            """
            try:
                project_path_obj = Path(project_path).resolve()
                result = self.orchestrator.analyze_project(project_path_obj)
                
                # Collect issues
                issues = []
                for file_result in result.files:
                    for issue in file_result.issues:
                        issues.append({
                            "file": str(file_result.file_path.relative_to(result.project_path)),
                            "element": issue.element.name if issue.element else None,
                            "severity": issue.severity,
                            "message": issue.message,
                            "suggestion": issue.suggestion,
                            "line_number": issue.line_number
                        })
                
                return {
                    "project_path": str(result.project_path),
                    "total_issues": len(issues),
                    "issues": issues,
                    "issues_by_severity": result.issues_by_severity
                }
            except Exception as e:
                logger.error(f"Error in check_documentation: {e}")
                return {"error": str(e)}
    
    def _register_resources(self):
        """Register MCP resources."""
        from mcp.types import Resource
        
        # Register a resource for documentation files
        self.server.add_resource(
            Resource(
                name="documentation-files",
                uri="file://*",
                title="Documentation Files"
            )
        )
    
    def _register_prompts(self):
        """Register MCP prompts."""
        from mcp.types import Prompt
        
        # Register a prompt for documentation analysis
        self.server.add_prompt(
            Prompt(
                name="documentation-analysis",
                title="Documentation Analysis",
                description="Analyze the documentation quality of the provided codebase and suggest improvements."
            )
        )
    
    async def run(self):
        """Run the MCP server."""
        await self.server.run("stdio")


def main():
    """Main entry point."""
    try:
        # Check if running as MCP server or CLI
        if len(sys.argv) > 1 and sys.argv[1] in ["--mcp", "mcp"]:
            # Run as MCP server
            server = DocumentationMCPServer()
            # Use the server's built-in run method which handles the event loop
            server.server.run("stdio")
        else:
            # Run as CLI (import and call CLI)
            from .cli import cli
            cli()
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
