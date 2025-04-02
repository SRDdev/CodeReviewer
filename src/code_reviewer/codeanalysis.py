import os
import ast
import logging
from typing import Dict, List, Set, Tuple
import re
import concurrent.futures
from collections import defaultdict
import json
import datetime
from pathlib import Path

from src.code_reviewer.codequality import CodeQualityVisitor
from src.code_reviewer.complexity import ComplexityVisitor
from src.code_reviewer.errorhandling import ErrorHandlingVisitor
from src.code_reviewer.scaleability import ScalabilityVisitor


class CodeQualityAnalyzer:
    """A tool to analyze Python code quality for production readiness and scalability."""
    
    def __init__(self, root_dir: str, output_dir: str = "code_quality_reports"):
        """Initialize the analyzer with the root directory to scan."""
        self.root_dir = os.path.abspath(root_dir)
        self.output_dir = output_dir
        self.file_extensions = {'.py'}
        self.issues_found = defaultdict(list)
        self.file_ratings = {}
        self.file_metrics = {}
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Set up logging
        logging.basicConfig(
            filename=f"{output_dir}/analysis_log.txt",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging

    def scan_files(self) -> List[str]:
        """Scan and return all code files with supported extensions."""
        file_paths = []
        
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                file_ext = os.path.splitext(file)[1]
                if file_ext in self.file_extensions:
                    file_path = os.path.join(root, file)
                    # Skip files in the output directory
                    if os.path.abspath(file_path).startswith(os.path.abspath(self.output_dir)):
                        continue
                    file_paths.append(file_path)
        
        self.logger.info(f"Found {len(file_paths)} code files to analyze")
        return file_paths

    def analyze_all(self) -> Dict:
        """Analyze all code files and generate reports."""
        file_paths = self.scan_files()
        
        # Process files in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(self.analyze_file, file_paths))
        
        # Calculate ratings for all files
        self._calculate_file_ratings()
        
        # Generate summary report
        self._generate_summary_report()
        
        # Generate final comprehensive report
        self._generate_final_report()
        
        return self.issues_found

    def analyze_file(self, file_path: str) -> Dict:
        """Analyze a single file for code quality issues."""
        relative_path = os.path.relpath(file_path, self.root_dir)
        self.logger.info(f"Analyzing {relative_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Initialize metrics for this file
            self.file_metrics[file_path] = {
                'lines_of_code': len(content.split('\n')),
                'issue_counts': defaultdict(int),
                'severity_counts': defaultdict(int),
                'complexity_score': 0,
                'maintainability_score': 0,
                'scalability_score': 0,
                'security_score': 0,
                'error_handling_score': 0
            }
            
            # Python-specific analysis
            if file_path.endswith('.py'):
                issues = self._analyze_python_file(content, file_path)
                
                if issues:
                    self.issues_found[file_path] = issues
                    
                    # Count issues by type and severity
                    for issue in issues:
                        self.file_metrics[file_path]['issue_counts'][issue['type']] += 1
                        self.file_metrics[file_path]['severity_counts'][issue['severity']] += 1
                    
                    # Write report for this file
                    self._write_file_report(file_path, issues)
                    
            return {file_path: issues}
                
        except Exception as e:
            error_msg = f"Error analyzing {relative_path}: {str(e)}"
            self.logger.error(error_msg)
            self.issues_found[file_path].append({
                'type': 'ANALYSIS_ERROR',
                'message': error_msg,
                'line': 0,
                'severity': 'ERROR'
            })
            self.file_metrics[file_path]['severity_counts']['ERROR'] += 1
            return {file_path: self.issues_found[file_path]}
    
    def _analyze_python_file(self, content: str, file_path: str) -> List[Dict]:
        """Perform Python-specific code analysis."""
        issues = []
        
        # Try to parse the AST
        try:
            tree = ast.parse(content)
            
            # Check for error handling
            error_handling_issues = self._check_error_handling(tree, content)
            issues.extend(error_handling_issues)
            
            # Check for code quality
            quality_issues = self._check_code_quality(tree, content)
            issues.extend(quality_issues)
            
            # Check for scalability
            scalability_issues = self._check_scalability(tree, content)
            issues.extend(scalability_issues)
            
            # Line-by-line analysis for patterns
            line_issues = self._analyze_lines(content)
            issues.extend(line_issues)
            
            # Calculate complexity metrics
            self._calculate_complexity_metrics(tree, file_path)
            
        except SyntaxError as e:
            issues.append({
                'type': 'SYNTAX_ERROR',
                'message': f"Syntax error: {str(e)}",
                'line': e.lineno if hasattr(e, 'lineno') else 0,
                'severity': 'ERROR'
            })
        
        return issues
    
    def _check_error_handling(self, tree: ast.AST, content: str) -> List[Dict]:
        """Check for proper error handling."""
        issues = []
        error_visitor = ErrorHandlingVisitor()
        error_visitor.visit(tree)
        
        # Functions/methods that lack try-except blocks
        for func_name, func_line in error_visitor.functions_without_try_except:
            issues.append({
                'type': 'MISSING_ERROR_HANDLING',
                'message': f"Function '{func_name}' has no error handling",
                'line': func_line,
                'severity': 'WARNING'
            })
        
        # Bare except blocks
        for line_no in error_visitor.bare_except_lines:
            issues.append({
                'type': 'BARE_EXCEPT',
                'message': "Using bare 'except:' is not recommended for production code",
                'line': line_no,
                'severity': 'WARNING'
            })
            
        # IO operations without error handling
        for line_no, operation in error_visitor.io_without_error_handling:
            issues.append({
                'type': 'UNHANDLED_IO',
                'message': f"IO operation '{operation}' without error handling",
                'line': line_no,
                'severity': 'WARNING'
            })
            
        return issues
    
    def _check_code_quality(self, tree: ast.AST, content: str) -> List[Dict]:
        """Check for code quality issues."""
        issues = []
        quality_visitor = CodeQualityVisitor()
        quality_visitor.visit(tree)
        
        # Check for long functions
        for func_name, line_no, num_lines in quality_visitor.long_functions:
            issues.append({
                'type': 'LONG_FUNCTION',
                'message': f"Function '{func_name}' is too long ({num_lines} lines)",
                'line': line_no,
                'severity': 'INFO'
            })
        
        # Check for complex functions
        for func_name, line_no, complexity in quality_visitor.complex_functions:
            issues.append({
                'type': 'COMPLEX_FUNCTION',
                'message': f"Function '{func_name}' has high cyclomatic complexity ({complexity})",
                'line': line_no,
                'severity': 'WARNING'
            })
        
        # Check for missing docstrings
        for item_type, name, line_no in quality_visitor.missing_docstrings:
            issues.append({
                'type': 'MISSING_DOCSTRING',
                'message': f"{item_type} '{name}' is missing a docstring",
                'line': line_no,
                'severity': 'INFO'
            })
            
        # Check for unused imports
        for import_name, line_no in quality_visitor.possibly_unused_imports:
            issues.append({
                'type': 'UNUSED_IMPORT',
                'message': f"Import '{import_name}' might be unused",
                'line': line_no,
                'severity': 'INFO'
            })
        
        return issues
    
    def _check_scalability(self, tree: ast.AST, content: str) -> List[Dict]:
        """Check for code scalability issues."""
        issues = []
        scalability_visitor = ScalabilityVisitor()
        scalability_visitor.visit(tree)
        
        # Check for hardcoded configurations
        for line_no, const_name in scalability_visitor.hardcoded_configs:
            issues.append({
                'type': 'HARDCODED_CONFIG',
                'message': f"Hardcoded configuration value '{const_name}'",
                'line': line_no,
                'severity': 'INFO'
            })
        
        # Check for resource management issues
        for resource_type, line_no in scalability_visitor.resource_issues:
            issues.append({
                'type': 'RESOURCE_MANAGEMENT',
                'message': f"Resource '{resource_type}' might not be properly managed",
                'line': line_no,
                'severity': 'WARNING'
            })
            
        # Check for potential bottlenecks
        for bottleneck_type, line_no, code in scalability_visitor.potential_bottlenecks:
            issues.append({
                'type': 'POTENTIAL_BOTTLENECK',
                'message': f"{bottleneck_type} bottleneck: {code}",
                'line': line_no,
                'severity': 'WARNING'
            })
        
        return issues
    
    def _analyze_lines(self, content: str) -> List[Dict]:
        """Analyze code line by line for various patterns."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for overly long lines
            if len(line) > 100:
                issues.append({
                    'type': 'LONG_LINE',
                    'message': f"Line exceeds 100 characters ({len(line)})",
                    'line': i,
                    'severity': 'INFO'
                })
            
            # Check for TODO comments
            if re.search(r'#\s*TODO', line):
                issues.append({
                    'type': 'TODO_COMMENT',
                    'message': "TODO comment found",
                    'line': i,
                    'severity': 'INFO'
                })
                
            # Check for print statements (often left in after debugging)
            if re.search(r'\bprint\s*\(', line) and not re.search(r'def\s+print', line):
                issues.append({
                    'type': 'PRINT_STATEMENT',
                    'message': "Print statement should be replaced with proper logging",
                    'line': i,
                    'severity': 'INFO'
                })
                
            # Check for potential SQL injection
            if re.search(r'execute\s*\(\s*["\'].*\%', line) or re.search(r'execute\s*\(\s*f["\']', line):
                issues.append({
                    'type': 'SQL_INJECTION_RISK',
                    'message': "Potential SQL injection vulnerability",
                    'line': i,
                    'severity': 'ERROR'
                })
                
        return issues
    
    def _calculate_complexity_metrics(self, tree: ast.AST, file_path: str) -> None:
        """Calculate complexity metrics for a file."""
        # Calculate cyclomatic complexity
        complexity_visitor = ComplexityVisitor()
        complexity_visitor.visit(tree)
        
        # Store complexity metrics
        self.file_metrics[file_path]['complexity_score'] = complexity_visitor.file_complexity
        self.file_metrics[file_path]['avg_func_complexity'] = complexity_visitor.avg_function_complexity
        self.file_metrics[file_path]['max_func_complexity'] = complexity_visitor.max_function_complexity
        self.file_metrics[file_path]['functions_count'] = complexity_visitor.functions_count
        self.file_metrics[file_path]['classes_count'] = complexity_visitor.classes_count
        
    def _calculate_file_ratings(self) -> None:
        """Calculate ratings for each file based on metrics and issues."""
        for file_path, metrics in self.file_metrics.items():
            # Initialize scores
            error_handling_score = 10.0
            maintainability_score = 10.0
            scalability_score = 10.0
            security_score = 10.0
            
            # Severity penalties
            severity_penalties = {
                'ERROR': 2.0,
                'WARNING': 1.0,
                'INFO': 0.2
            }
            
            # Issue type categories
            error_handling_issues = ['MISSING_ERROR_HANDLING', 'BARE_EXCEPT', 'UNHANDLED_IO']
            maintainability_issues = ['LONG_FUNCTION', 'COMPLEX_FUNCTION', 'MISSING_DOCSTRING', 
                                      'UNUSED_IMPORT', 'LONG_LINE', 'TODO_COMMENT', 'PRINT_STATEMENT']
            scalability_issues = ['HARDCODED_CONFIG', 'RESOURCE_MANAGEMENT', 'POTENTIAL_BOTTLENECK']
            security_issues = ['SQL_INJECTION_RISK']
            
            # Calculate penalties for each issue
            for issue_type, count in metrics['issue_counts'].items():
                if issue_type in error_handling_issues:
                    error_handling_score -= count * 0.5
                elif issue_type in maintainability_issues:
                    maintainability_score -= count * 0.3
                elif issue_type in scalability_issues:
                    scalability_score -= count * 0.4
                elif issue_type in security_issues:
                    security_score -= count * 2.0
            
            # Apply severity penalties
            for severity, count in metrics['severity_counts'].items():
                penalty = severity_penalties.get(severity, 0) * count
                if severity == 'ERROR':
                    security_score -= penalty
                    error_handling_score -= penalty * 0.5
                elif severity == 'WARNING':
                    error_handling_score -= penalty * 0.3
                    maintainability_score -= penalty * 0.3
                    scalability_score -= penalty * 0.3
                elif severity == 'INFO':
                    maintainability_score -= penalty * 0.2
            
            # Adjust based on complexity
            if metrics['complexity_score'] > 50:
                maintainability_score -= 2.0
                scalability_score -= 1.0
            elif metrics['complexity_score'] > 30:
                maintainability_score -= 1.0
                scalability_score -= 0.5
            
            # Normalize scores (0-10 range)
            error_handling_score = max(0, min(10, error_handling_score))
            maintainability_score = max(0, min(10, maintainability_score))
            scalability_score = max(0, min(10, scalability_score))
            security_score = max(0, min(10, security_score))
            
            # Calculate overall score (weighted average)
            overall_score = (
                error_handling_score * 0.25 +
                maintainability_score * 0.35 +
                scalability_score * 0.25 +
                security_score * 0.15
            )
            
            # Assign letter grade
            grade = self._score_to_grade(overall_score)
            
            # Store ratings
            self.file_ratings[file_path] = {
                'error_handling_score': round(error_handling_score, 1),
                'maintainability_score': round(maintainability_score, 1),
                'scalability_score': round(scalability_score, 1),
                'security_score': round(security_score, 1),
                'overall_score': round(overall_score, 1),
                'grade': grade
            }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numerical score to letter grade."""
        if score >= 9.0:
            return 'A+'
        elif score >= 8.5:
            return 'A'
        elif score >= 8.0:
            return 'A-'
        elif score >= 7.5:
            return 'B+'
        elif score >= 7.0:
            return 'B'
        elif score >= 6.5:
            return 'B-'
        elif score >= 6.0:
            return 'C+'
        elif score >= 5.5:
            return 'C'
        elif score >= 5.0:
            return 'C-'
        elif score >= 4.0:
            return 'D'
        else:
            return 'F'
    
    def _write_file_report(self, file_path: str, issues: List[Dict]) -> None:
        """Write a report for a specific file."""
        relative_path = os.path.relpath(file_path, self.root_dir)
        name = relative_path.replace('/', '_').replace('\\\\', '_')
        report_filename = f"{name}_report.txt"
        report_path = os.path.join(self.output_dir, report_filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(f"Code Quality Report for {relative_path}\n")
            f.write(f"{'=' * 80}\n\n")
            
            # Group issues by severity
            severity_groups = {
                'ERROR': [],
                'WARNING': [],
                'INFO': []
            }
            
            for issue in issues:
                severity_groups[issue['severity']].append(issue)
            
            # Write issues by severity
            for severity in ['ERROR', 'WARNING', 'INFO']:
                if severity_groups[severity]:
                    f.write(f"{severity} issues ({len(severity_groups[severity])}):\n")
                    f.write(f"{'-' * 80}\n")
                    
                    for issue in severity_groups[severity]:
                        f.write(f"Line {issue['line']}: {issue['type']} - {issue['message']}\n")
                    
                    f.write("\n")
        
        self.logger.info(f"Report for {relative_path} written to {report_path}")
    
    def _generate_summary_report(self) -> None:
        """Generate a summary report of all issues."""
        summary_path = os.path.join(self.output_dir, "summary_report.txt")
        
        with open(summary_path, 'w') as f:
            f.write("Code Quality Analysis Summary Report\n")
            f.write(f"{'=' * 80}\n\n")
            
            total_files = len(self.scan_files())
            files_with_issues = len(self.issues_found)
            total_issues = sum(len(issues) for issues in self.issues_found.values())
            
            f.write(f"Total files analyzed: {total_files}\n")
            f.write(f"Files with issues: {files_with_issues}\n")
            f.write(f"Total issues found: {total_issues}\n\n")
            
            # Count issues by type and severity
            issue_types = defaultdict(int)
            severity_counts = defaultdict(int)
            
            for file_path, issues in self.issues_found.items():
                for issue in issues:
                    issue_types[issue['type']] += 1
                    severity_counts[issue['severity']] += 1
            
            # Write severity summary
            f.write("Issues by severity:\n")
            f.write(f"{'-' * 80}\n")
            for severity, count in severity_counts.items():
                f.write(f"{severity}: {count}\n")
            f.write("\n")
            
            # Write issue type summary
            f.write("Issues by type:\n")
            f.write(f"{'-' * 80}\n")
            for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{issue_type}: {count}\n")
            f.write("\n")
            
            # Files with most issues
            f.write("Files with most issues:\n")
            f.write(f"{'-' * 80}\n")
            files_by_issues = sorted(self.issues_found.items(), key=lambda x: len(x[1]), reverse=True)
            for file_path, issues in files_by_issues[:10]:  # Top 10 files
                relative_path = os.path.relpath(file_path, self.root_dir)
                f.write(f"{relative_path}: {len(issues)} issues\n")
            
            f.write("\n")
            
            # Files by rating
            f.write("File Ratings:\n")
            f.write(f"{'-' * 80}\n")
            f.write(f"{'File':<40} {'Grade':<5} {'Overall':<8} {'Error':<8} {'Maint.':<8} {'Scale.':<8} {'Security':<8}\n")
            f.write(f"{'-' * 80}\n")
            
            sorted_ratings = sorted(
                self.file_ratings.items(), 
                key=lambda x: x[1]['overall_score'], 
                reverse=True
            )
            
            for file_path, ratings in sorted_ratings:
                relative_path = os.path.relpath(file_path, self.root_dir)
                short_path = self._shorten_path(relative_path, 39)
                f.write(f"{short_path:<40} {ratings['grade']:<5} "
                        f"{ratings['overall_score']:<8.1f} "
                        f"{ratings['error_handling_score']:<8.1f} "
                        f"{ratings['maintainability_score']:<8.1f} "
                        f"{ratings['scalability_score']:<8.1f} "
                        f"{ratings['security_score']:<8.1f}\n")
        
        self.logger.info(f"Summary report written to {summary_path}")
    
    def _generate_final_report(self) -> None:
        """Generate a comprehensive final report with recommendations."""
        report_path = os.path.join(self.output_dir, "final_report.md")
        
        with open(report_path, 'w') as f:
            # Title
            f.write("# Code Quality Analysis Final Report\n\n")
            f.write(f"**Generated on:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            
            total_files = len(self.scan_files())
            files_with_issues = len(self.issues_found)
            total_issues = sum(len(issues) for issues in self.issues_found.values())
            
            # Calculate average ratings
            if self.file_ratings:
                avg_overall = sum(r['overall_score'] for r in self.file_ratings.values()) / len(self.file_ratings)
                avg_error = sum(r['error_handling_score'] for r in self.file_ratings.values()) / len(self.file_ratings)
                avg_maint = sum(r['maintainability_score'] for r in self.file_ratings.values()) / len(self.file_ratings)
                avg_scale = sum(r['scalability_score'] for r in self.file_ratings.values()) / len(self.file_ratings)
                avg_security = sum(r['security_score'] for r in self.file_ratings.values()) / len(self.file_ratings)
                
                overall_grade = self._score_to_grade(avg_overall)
            else:
                avg_overall = avg_error = avg_maint = avg_scale = avg_security = 0
                overall_grade = "N/A"
            
            f.write(f"This analysis examined **{total_files}** Python files and found issues in **{files_with_issues}** files "
                    f"with a total of **{total_issues}** issues identified.\n\n")
            
            f.write(f"**Overall Codebase Grade: {overall_grade}** ({avg_overall:.1f}/10)\n\n")
            
            f.write("### Key Metrics\n\n")
            f.write("| Metric | Score (0-10) | Grade |\n")
            f.write("|--------|-------------|-------|\n")
            f.write(f"| Overall Quality | {avg_overall:.1f} | {overall_grade} |\n")
            f.write(f"| Error Handling | {avg_error:.1f} | {self._score_to_grade(avg_error)} |\n")
            f.write(f"| Maintainability | {avg_maint:.1f} | {self._score_to_grade(avg_maint)} |\n")
            f.write(f"| Scalability | {avg_scale:.1f} | {self._score_to_grade(avg_scale)} |\n")
            f.write(f"| Security | {avg_security:.1f} | {self._score_to_grade(avg_security)} |\n\n")
            
            # Issue Summary
            f.write("## Issue Summary\n\n")
            
            # Severity distribution
            severity_counts = defaultdict(int)
            for file_path, issues in self.issues_found.items():
                for issue in issues:
                    severity_counts[issue['severity']] += 1
            
            f.write("### Issues by Severity\n\n")
            f.write("| Severity | Count | % of Total |\n")
            f.write("|----------|-------|------------|\n")
            for severity in ['ERROR', 'WARNING', 'INFO']:
                count = severity_counts.get(severity, 0)
                percentage = (count / total_issues * 100) if total_issues > 0 else 0
                f.write(f"| {severity} | {count} | {percentage:.1f}% |\n")
            f.write("\n")
            
            # Issue types
            issue_types = defaultdict(int)
            for file_path, issues in self.issues_found.items():
                for issue in issues:
                    issue_types[issue['type']] += 1
            
            f.write("### Top Issue Types\n\n")
            f.write("| Issue Type | Count | % of Total |\n")
            f.write("|------------|-------|------------|\n")
            
            sorted_issues = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)
            for issue_type, count in sorted_issues[:10]:  # Top 10 issue types
                percentage = (count / total_issues * 100) if total_issues > 0 else 0
                f.write(f"| {issue_type} | {count} | {percentage:.1f}% |\n")
            f.write("\n")
            
            # File Ratings
            f.write("## File Ratings\n\n")
            f.write("### Top Rated Files\n\n")
            f.write("| File | Grade | Overall | Error | Maintainability | Scalability | Security |\n")
            f.write("|------|-------|---------|-------|----------------|-------------|----------|\n")
            
            sorted_ratings = sorted(
                self.file_ratings.items(), 
                key=lambda x: x[1]['overall_score'], 
                reverse=True
            )
            
            for file_path, ratings in sorted_ratings[:5]:  # Top 5 files
                relative_path = os.path.relpath(file_path, self.root_dir)
                short_path = self._shorten_path(relative_path, 30)
                f.write(f"| {short_path} | {ratings['grade']} | {ratings['overall_score']:.1f} | "
                        f"{ratings['error_handling_score']:.1f} | {ratings['maintainability_score']:.1f} | "
                        f"{ratings['scalability_score']:.1f} | {ratings['security_score']:.1f} |\n")
            
            f.write("\n")
            
            f.write("### Lowest Rated Files\n\n")
            f.write("| File | Grade | Overall | Error | Maintainability | Scalability | Security |\n")
            f.write("|------|-------|---------|-------|----------------|-------------|----------|\n")
            
            for file_path, ratings in sorted_ratings[-5:]:  # Bottom 5 files
                relative_path = os.path.relpath(file_path, self.root_dir)
                short_path = self._shorten_path(relative_path, 30)
                f.write(f"| {short_path} | {ratings['grade']} | {ratings['overall_score']:.1f} | "
                        f"{ratings['error_handling_score']:.1f} | {ratings['maintainability_score']:.1f} | "
                        f"{ratings['scalability_score']:.1f} | {ratings['security_score']:.1f} |\n")
            
            f.write("\n")
            
            # Key Recommendations
            f.write("## Key Recommendations\n\n")
            
            # Generate recommendations based on the most common issues
            recommendations = self._generate_recommendations(issue_types)
            for i, (category, recs) in enumerate(recommendations.items(), 1):
                f.write(f"### {i}. {category}\n\n")
                for j, rec in enumerate(recs, 1):
                    f.write(f"{j}. {rec}\n")
                f.write("\n")
            
            # Appendix with all files
            f.write("## Appendix: All Files\n\n")
            f.write("| File | Grade | Overall | Issues |\n")
            f.write("|------|-------|---------|--------|\n")
            
            for file_path, ratings in sorted_ratings:
                relative_path = os.path.relpath(file_path, self.root_dir)
                short_path = self._shorten_path(relative_path, 50)
                issues_count = len(self.issues_found.get(file_path, []))
                f.write(f"| {short_path} | {ratings['grade']} | {ratings['overall_score']:.1f} | {issues_count} |\n")
        
        self.logger.info(f"Final report written to {report_path}")
        
        # Generate a JSON version of the data for potential future use
        # Generate a JSON version of the data for potential future use
        json_path = os.path.join(self.output_dir, "analysis_data.json")
        
        json_data = {
            'summary': {
                'total_files': total_files,
                'files_with_issues': files_with_issues,
                'total_issues': total_issues,
                'average_scores': {
                    'overall': avg_overall,
                    'error_handling': avg_error,
                    'maintainability': avg_maint,
                    'scalability': avg_scale,
                    'security': avg_security,
                    'grade': overall_grade
                },
                'severity_counts': dict(severity_counts),
                'issue_types': dict(issue_types)
            },
            'file_ratings': self.file_ratings,
            'file_metrics': self.file_metrics
        }
        
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2, default=lambda x: str(x) if isinstance(x, (Path, set)) else x)
            
        self.logger.info(f"Analysis data written to {json_path}")
    
    def _generate_recommendations(self, issue_types: Dict[str, int]) -> Dict[str, List[str]]:
        """Generate recommendations based on issue types."""
        recommendations = {
            "Error Handling": [],
            "Code Maintainability": [],
            "Scalability": [],
            "Security": []
        }
        
        # Error handling recommendations
        if issue_types.get('MISSING_ERROR_HANDLING', 0) > 0:
            recommendations["Error Handling"].append(
                "Add proper error handling to functions that lack it, especially those performing I/O operations."
            )
        
        if issue_types.get('BARE_EXCEPT', 0) > 0:
            recommendations["Error Handling"].append(
                "Replace bare 'except:' clauses with specific exception handlers to avoid masking critical errors."
            )
        
        if issue_types.get('UNHANDLED_IO', 0) > 0:
            recommendations["Error Handling"].append(
                "Use try-except blocks or context managers (with statement) for all file and network operations."
            )
        
        # Maintainability recommendations
        if issue_types.get('MISSING_DOCSTRING', 0) > 0:
            recommendations["Code Maintainability"].append(
                "Add docstrings to all modules, classes, and functions to improve code clarity and maintainability."
            )
        
        if issue_types.get('LONG_FUNCTION', 0) > 0 or issue_types.get('COMPLEX_FUNCTION', 0) > 0:
            recommendations["Code Maintainability"].append(
                "Refactor long or complex functions into smaller, more focused ones with clear responsibilities."
            )
        
        if issue_types.get('UNUSED_IMPORT', 0) > 0:
            recommendations["Code Maintainability"].append(
                "Remove unused imports to reduce code clutter and improve performance."
            )
        
        if issue_types.get('PRINT_STATEMENT', 0) > 0:
            recommendations["Code Maintainability"].append(
                "Replace print statements with proper logging for better debugging and monitoring in production."
            )
        
        if issue_types.get('TODO_COMMENT', 0) > 0:
            recommendations["Code Maintainability"].append(
                "Address TODO comments in the code or convert them to tracked issues in your project management system."
            )
        
        # Scalability recommendations
        if issue_types.get('HARDCODED_CONFIG', 0) > 0:
            recommendations["Scalability"].append(
                "Move hardcoded configuration values to configuration files or environment variables."
            )
        
        if issue_types.get('POTENTIAL_BOTTLENECK', 0) > 0:
            recommendations["Scalability"].append(
                "Review and optimize potential bottlenecks, particularly in data processing and database operations."
            )
        
        if issue_types.get('RESOURCE_MANAGEMENT', 0) > 0:
            recommendations["Scalability"].append(
                "Ensure proper resource management with context managers (with statements) for files, connections, etc."
            )
        
        # Security recommendations
        if issue_types.get('SQL_INJECTION_RISK', 0) > 0:
            recommendations["Security"].append(
                "Use parameterized queries or ORM to prevent SQL injection vulnerabilities."
            )
        
        # Generic recommendations if not enough specific ones
        if not recommendations["Error Handling"]:
            recommendations["Error Handling"].append(
                "Implement comprehensive error handling throughout the codebase, focusing on critical operations."
            )
            
        if not recommendations["Code Maintainability"]:
            recommendations["Code Maintainability"].append(
                "Follow PEP 8 style guidelines and add documentation to improve code readability."
            )
            
        if not recommendations["Scalability"]:
            recommendations["Scalability"].append(
                "Design for scalability by focusing on efficient algorithms and resource management."
            )
            
        if not recommendations["Security"]:
            recommendations["Security"].append(
                "Apply security best practices for input validation, authentication, and sensitive data handling."
            )
            
        return recommendations
    
    def _shorten_path(self, path: str, max_length: int) -> str:
        """Shorten a path to fit within max_length characters."""
        if len(path) <= max_length:
            return path
        
        parts = path.split(os.sep)
        if len(parts) <= 2:
            return path[-max_length:]
        
        # Keep first and last parts, shorten middle parts
        first = parts[0]
        last = parts[-1]
        
        # Calculate how much space we have for middle parts
        middle_length = max_length - len(first) - len(last) - 5  # 5 for '/...//'
        
        if middle_length < 3:
            # Not enough space, just truncate
            return '...' + path[-(max_length-3):]
        
        return f"{first}/.../{last}"
