"""Command-line interface for the MCP Documentation Server."""

import click
import sys
from pathlib import Path
from typing import Optional

from .core.orchestrator import DocumentationOrchestrator
from .config import ServerConfig
from .logger import get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option()
def cli():
    """MCP Documentation Server - Automate and enhance code documentation."""
    pass


@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('-c', '--config', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('-o', '--output', type=click.Path(), 
              help='Output directory for generated documentation')
@click.option('-v', '--verbose', is_flag=True, 
              help='Enable verbose output')
def analyze(project_path: str, config: Optional[str], output: Optional[str], verbose: bool):
    """Analyze a project for documentation issues."""
    try:
        # Convert paths
        project_path_obj = Path(project_path).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Initialize orchestrator
        orchestrator = DocumentationOrchestrator(config_path)
        
        # Override output directory if specified
        if output:
            orchestrator.config.output.output_dir = output
        
        # Perform analysis
        project_result = orchestrator.analyze_project(project_path_obj)
        
        # Display results
        _display_analysis_results(project_result, verbose)
        
        click.echo(f"\nAnalysis completed successfully.")
        click.echo(f"Documentation coverage: {project_result.overall_coverage:.1%}")
        click.echo(f"Issues found: {sum(project_result.issues_by_severity.values())}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Documentation generation functionality removed per project focus


@cli.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('-c', '--config', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('-o', '--output', type=click.Path(), 
              help='Output directory for generated documentation')
def check(project_path: str, config: Optional[str], output: Optional[str]):
    """Check documentation without making changes."""
    try:
        # Convert paths
        project_path_obj = Path(project_path).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Initialize orchestrator
        orchestrator = DocumentationOrchestrator(config_path)
        
        # Override output directory if specified
        if output:
            orchestrator.config.output.output_dir = output
        
        # Perform analysis only
        project_result = orchestrator.analyze_project(project_path_obj)
        
        # Display issues
        _display_issues(project_result)
        
        # Exit with error code if issues found
        total_issues = sum(project_result.issues_by_severity.values())
        if total_issues > 0:
            click.echo(f"\nFound {total_issues} documentation issues.")
            sys.exit(1)
        else:
            click.echo("\nNo documentation issues found.")
            
    except Exception as e:
        logger.error(f"Error during documentation check: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _display_analysis_results(project_result, verbose: bool = False):
    """Display analysis results in a formatted way."""
    click.echo(f"\n=== Documentation Analysis Results ===")
    click.echo(f"Project: {project_result.project_path.name}")
    click.echo(f"Files analyzed: {len(project_result.files)}")
    click.echo(f"Total elements: {project_result.total_elements}")
    click.echo(f"Documented elements: {project_result.documented_elements}")
    click.echo(f"Documentation coverage: {project_result.overall_coverage:.1%}")
    
    if verbose and project_result.coverage_by_language:
        click.echo(f"\nCoverage by language:")
        for lang, coverage in project_result.coverage_by_language.items():
            click.echo(f"  {lang}: {coverage:.1%}")
    
    if project_result.issues_by_severity:
        click.echo(f"\nIssues by severity:")
        for severity, count in project_result.issues_by_severity.items():
            click.echo(f"  {severity.title()}: {count}")


def _display_issues(project_result):
    """Display documentation issues."""
    total_issues = sum(project_result.issues_by_severity.values())
    if total_issues == 0:
        click.echo("No documentation issues found.")
        return
    
    click.echo(f"\n=== Documentation Issues ({total_issues} found) ===")
    
    # Group issues by file
    issues_by_file = {}
    for file_result in project_result.files:
        if file_result.issues:
            rel_path = file_result.file_path.relative_to(project_result.project_path)
            issues_by_file[str(rel_path)] = file_result.issues
    
    # Display issues
    for file_path, issues in issues_by_file.items():
        click.echo(f"\n{file_path}:")
        for issue in issues:
            severity_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(issue.severity, '⚪')
            
            click.echo(f"  {severity_icon} {issue.message}")
            if issue.suggestion:
                click.echo(f"    💡 Suggestion: {issue.suggestion}")


if __name__ == '__main__':
    cli()
