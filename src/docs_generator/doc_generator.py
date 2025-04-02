#!/usr/bin/env python3
"""
API Documentation Generator

This script searches for FastAPI router files in a project and automatically generates
comprehensive Markdown documentation for all API endpoints.

Usage:
    python api_docs_generator.py --path /path/to/project [--output docs/api]
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set


class RouterDocsGenerator:
    """Generate API documentation from FastAPI router files."""
    
    ROUTER_PATTERNS = [
        r'(\w+)\s*=\s*(?:APIRouter|FastAPI)\s*\(',  # Match router initialization
        r'from\s+fastapi\s+import\s+(?:.*?APIRouter|.*?FastAPI)',  # Import statements
        r'@(?:\w+)\.(get|post|put|delete|patch)',  # Router decorators
    ]
    
    def __init__(self, project_path: str, output_path: str = None, verbose: bool = False):
        """
        Initialize the generator with project path and output location.
        
        Args:
            project_path: Path to the project root
            output_path: Path where documentation will be saved
            verbose: Whether to print detailed progress information
        """
        self.project_path = os.path.abspath(project_path)
        self.output_path = output_path or os.path.join(self.project_path, "docs", "api")
        self.verbose = verbose
        
        # Ensure output directory exists
        os.makedirs(self.output_path, exist_ok=True)
        
        if self.verbose:
            print(f"Project path: {self.project_path}")
            print(f"Output path: {self.output_path}")
    
    def log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def find_router_files(self) -> List[str]:
        """
        Scan project directory for potential router files.
        
        Returns:
            List of paths to router files
        """
        router_files = []
        router_file_patterns = [
            r'.*router.*\.py$',  # Files with 'router' in the name
            r'.*routes.*\.py$',   # Files with 'routes' in the name
            r'.*endpoints.*\.py$', # Files with 'endpoints' in the name
            r'.*api\.py$',        # api.py files
        ]
        
        # Compile patterns for faster matching
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in router_file_patterns]
        
        self.log("Searching for router files...")
        
        for root, _, files in os.walk(self.project_path):
            # Skip virtual environments and hidden directories
            if '/venv/' in root or '/.venv/' in root or '/__pycache__/' in root or '/.git/' in root:
                continue
                
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                # Check if filename matches router patterns
                if any(pattern.match(file) for pattern in compiled_patterns):
                    router_files.append(os.path.join(root, file))
                    continue
                    
                # For other Python files, check content for router-related code
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if any(re.search(pattern, content) for pattern in self.ROUTER_PATTERNS):
                            router_files.append(file_path)
                except Exception as e:
                    self.log(f"Error reading {file_path}: {str(e)}")
        
        self.log(f"Found {len(router_files)} potential router files")
        return router_files
    
    def extract_docstring(self, lines: List[str], start_index: int) -> str:
        """
        Extract function docstring from the code.
        
        Args:
            lines: List of code lines
            start_index: Index of the function definition line
            
        Returns:
            Extracted docstring
        """
        docstring = ""
        i = start_index
        
        # Skip to the function definition line
        while i < len(lines) and not (lines[i].strip().startswith("def ") or 
                                      lines[i].strip().startswith("async def ")):
            i += 1
        
        if i >= len(lines):
            return docstring
            
        # Found function definition, move to next line
        i += 1
        
        # Skip blank lines after function definition
        while i < len(lines) and not lines[i].strip():
            i += 1
            
        if i >= len(lines):
            return docstring
            
        # Check for docstring
        if '"""' in lines[i] or "'''" in lines[i]:
            quote_type = '"""' if '"""' in lines[i] else "'''"
            start_line = lines[i].strip()
            
            # Check for single-line docstring
            if start_line.startswith(quote_type) and start_line.endswith(quote_type) and len(start_line) > 6:
                return start_line.strip(quote_type).strip()
                
            # Multi-line docstring
            doc_lines = []
            
            # Get content after opening quotes on the first line
            if start_line.startswith(quote_type):
                doc_lines.append(start_line[len(quote_type):].strip())
            else:
                # If quotes are indented, get content after them
                quote_pos = lines[i].find(quote_type)
                if quote_pos != -1:
                    doc_lines.append(lines[i][quote_pos + len(quote_type):].strip())
            
            i += 1
            # Collect lines until closing quotes
            while i < len(lines) and quote_type not in lines[i]:
                doc_lines.append(lines[i].strip())
                i += 1
                
            # Get content before closing quotes on the last line
            if i < len(lines) and quote_type in lines[i]:
                quote_pos = lines[i].find(quote_type)
                if quote_pos > 0:
                    doc_lines.append(lines[i][:quote_pos].strip())
                    
            docstring = " ".join(doc_lines).strip()
            
        return docstring
    
    def extract_request_body(self, lines: List[str], function_idx: int) -> Optional[str]:
        """
        Extract request body model from function parameters.
        
        Args:
            lines: List of code lines
            function_idx: Index of the function definition line
            
        Returns:
            Name of the request model or None
        """
        if function_idx >= len(lines):
            return None
            
        # Get function declaration
        func_line = lines[function_idx]
        
        # Check if function declaration spans multiple lines
        if "(" in func_line and ")" not in func_line:
            # Collect all lines of the parameter list
            params_lines = [func_line]
            i = function_idx + 1
            while i < len(lines) and ")" not in lines[i]:
                params_lines.append(lines[i])
                i += 1
                
            if i < len(lines):
                params_lines.append(lines[i])
                
            func_text = " ".join(params_lines)
        else:
            func_text = func_line
            
        # Look for common API parameter patterns
        param_patterns = [
            r'(?:body|data|request|payload|item|model):\s*(\w+)',
            r'(?:body|data|request|payload|item|model)\s*:\s*(?:Optional\[)?(\w+)(?:\])?',
        ]
        
        for pattern in param_patterns:
            match = re.search(pattern, func_text)
            if match:
                model_name = match.group(1)
                # Filter out built-in types
                if model_name.lower() not in ('str', 'int', 'float', 'bool', 'dict', 'list', 'any'):
                    return model_name
                    
        return None
    
    def extract_response_model(self, lines: List[str], decorator_idx: int) -> Optional[str]:
        """
        Extract response model from FastAPI decorator.
        
        Args:
            lines: List of code lines
            decorator_idx: Index of the decorator line
            
        Returns:
            Name of the response model or None
        """
        # Check current line and a few lines after for response_model
        for i in range(decorator_idx, min(decorator_idx + 3, len(lines))):
            response_match = re.search(r'response_model\s*=\s*(?:Optional\[)?(\w+)(?:\])?', lines[i])
            if response_match:
                return response_match.group(1)
                
        return None
    
    def extract_endpoints(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract API endpoints and their metadata from a router file.
        
        Args:
            file_path: Path to the router file
            
        Returns:
            List of endpoint dictionaries
        """
        endpoints = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                lines = content.splitlines()
                
            # Find router variable and prefix
            router_vars = {}
            router_pattern = re.compile(r'(\w+)\s*=\s*APIRouter\s*\(')
            prefix_pattern = re.compile(r'prefix\s*=\s*[\'"]([^\'"]+)[\'"]')
            tags_pattern = re.compile(r'tags\s*=\s*\[(.*?)\]')
            
            for i, line in enumerate(lines):
                router_match = router_pattern.search(line)
                if router_match:
                    router_var = router_match.group(1)
                    # Check for prefix in this line or next few lines
                    prefix = ""
                    for j in range(i, min(i + 3, len(lines))):
                        prefix_match = prefix_pattern.search(lines[j])
                        if prefix_match:
                            prefix = prefix_match.group(1)
                            break
                            
                    # Extract default tags
                    default_tags = []
                    for j in range(i, min(i + 3, len(lines))):
                        tags_match = tags_pattern.search(lines[j])
                        if tags_match:
                            tags_str = tags_match.group(1)
                            default_tags = [tag.strip().strip('"\'') for tag in tags_str.split(',')]
                            break
                            
                    router_vars[router_var] = {"prefix": prefix, "tags": default_tags}
            
            # Match endpoint decorators
            endpoint_pattern = re.compile(r'@(\w+)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]')
            method_tags_pattern = re.compile(r'tags\s*=\s*\[(.*?)\]')
            
            for i, line in enumerate(lines):
                endpoint_match = endpoint_pattern.search(line)
                if not endpoint_match:
                    continue
                    
                router_var, method, path = endpoint_match.groups()
                
                # Get router prefix if available
                router_info = router_vars.get(router_var, {"prefix": "", "tags": []})
                prefix = router_info["prefix"]
                default_tags = router_info["tags"]
                
                # Full path including prefix
                full_path = f"{prefix}{path}"
                
                # Extract decorator tags (override default tags)
                tags = default_tags.copy()
                tags_match = method_tags_pattern.search(line)
                if tags_match:
                    tags_str = tags_match.group(1)
                    tags = [tag.strip().strip('"\'') for tag in tags_str.split(',')]
                
                # Get response model
                response_model = self.extract_response_model(lines, i)
                
                # Find function definition
                function_name = "Unknown"
                for j in range(i, min(i + 5, len(lines))):
                    function_match = re.search(r'(?:async\s+)?def\s+(\w+)\s*\(', lines[j])
                    if function_match:
                        function_name = function_match.group(1)
                        docstring = self.extract_docstring(lines, j)
                        request_model = self.extract_request_body(lines, j)
                        
                        endpoint = {
                            "method": method.upper(),
                            "path": full_path,
                            "function": function_name,
                            "docstring": docstring,
                            "tags": tags,
                            "request_model": request_model,
                            "response_model": response_model,
                            "source_file": os.path.relpath(file_path, self.project_path)
                        }
                        
                        endpoints.append(endpoint)
                        break
            
            self.log(f"Extracted {len(endpoints)} endpoints from {os.path.basename(file_path)}")
            
        except Exception as e:
            self.log(f"Error processing {file_path}: {str(e)}")
            
        return endpoints
    
    def extract_models(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract Pydantic models defined in the router file.
        
        Args:
            file_path: Path to the router file
            
        Returns:
            Dictionary of model definitions
        """
        models = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Find all Pydantic model classes
            model_pattern = re.compile(r'class\s+(\w+)\s*\(\s*(?:BaseModel|pydantic\.BaseModel)\s*\):')
            model_matches = model_pattern.finditer(content)
            
            lines = content.splitlines()
            
            for match in model_matches:
                model_name = match.group(1)
                start_line = content[:match.start()].count('\n')
                
                # Extract model fields
                fields = {}
                i = start_line + 1
                while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('class '):
                    # Skip docstring, comments, or empty lines
                    if not lines[i].strip() or lines[i].strip().startswith('"""') or lines[i].strip().startswith('#'):
                        i += 1
                        continue
                        
                    # Match field definitions: name: type = default_value
                    field_match = re.match(r'\s*(\w+)\s*:\s*([^=]+)(?:\s*=\s*(.+))?', lines[i])
                    if field_match:
                        field_name, field_type, default_value = field_match.groups()
                        fields[field_name] = {
                            "type": field_type.strip(),
                            "default": default_value.strip() if default_value else None
                        }
                    
                    i += 1
                
                # Extract class docstring
                docstring = ""
                i = start_line + 1
                if i < len(lines) and ('"""' in lines[i] or "'''" in lines[i]):
                    quote_type = '"""' if '"""' in lines[i] else "'''"
                    if lines[i].strip().startswith(quote_type) and lines[i].strip().endswith(quote_type):
                        # Single line docstring
                        docstring = lines[i].strip().strip(quote_type).strip()
                    else:
                        # Multi-line docstring
                        doc_lines = []
                        while i < len(lines) and quote_type not in lines[i][lines[i].find(quote_type) + len(quote_type):]:
                            doc_line = lines[i].strip()
                            if doc_line.startswith(quote_type):
                                doc_lines.append(doc_line[len(quote_type):].strip())
                            else:
                                doc_lines.append(doc_line)
                            i += 1
                            
                        if i < len(lines):
                            end_quote_pos = lines[i].rfind(quote_type)
                            if end_quote_pos > 0:
                                doc_lines.append(lines[i][:end_quote_pos].strip())
                                
                        docstring = " ".join(doc_lines).strip()
                        
                models[model_name] = {
                    "fields": fields,
                    "docstring": docstring
                }
                
            self.log(f"Extracted {len(models)} models from {os.path.basename(file_path)}")
            
        except Exception as e:
            self.log(f"Error extracting models from {file_path}: {str(e)}")
            
        return models
    
    def generate_markdown(self, all_endpoints: Dict[str, List[Dict[str, Any]]], 
                         all_models: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
        """
        Generate Markdown documentation from extracted endpoints.
        
        Args:
            all_endpoints: Dictionary of endpoints by file
            all_models: Dictionary of models by file
            
        Returns:
            Generated Markdown content
        """
        # Flatten endpoints and models
        endpoints = []
        models = {}
        
        for file_path, file_endpoints in all_endpoints.items():
            endpoints.extend(file_endpoints)
            
        for file_path, file_models in all_models.items():
            for model_name, model_info in file_models.items():
                models[model_name] = model_info
        
        # Start the documentation
        md_content = "# API Documentation\n\n"
        
        # Build a table of contents
        md_content += "## Table of Contents\n\n"
        
        # Organize endpoints by tag then path
        organized_endpoints = {}
        
        for endpoint in endpoints:
            # Use the first tag as primary category or 'General' if none
            tag = endpoint["tags"][0] if endpoint["tags"] else "General"
            
            if tag not in organized_endpoints:
                organized_endpoints[tag] = {}
                
            # Group by first path segment, or 'root' if none
            path_parts = endpoint["path"].strip('/').split('/')
            base_path = path_parts[0] if path_parts else "root"
            
            if base_path not in organized_endpoints[tag]:
                organized_endpoints[tag][base_path] = []
                
            organized_endpoints[tag][base_path].append(endpoint)
        
        # Create table of contents entries
        for tag, paths in sorted(organized_endpoints.items()):
            md_content += f"- [{tag}](#category-{self.slugify(tag)})\n"
            for path in sorted(paths.keys()):
                md_content += f"  - [{path}](#path-{self.slugify(path)})\n"
                
        # Add models section if any exist
        if models:
            md_content += "- [Data Models](#data-models)\n"
            for model_name in sorted(models.keys()):
                md_content += f"  - [{model_name}](#model-{self.slugify(model_name)})\n"
                
        md_content += "\n---\n\n"
        
        # Generate detailed documentation for each category and path
        for tag, paths in sorted(organized_endpoints.items()):
            md_content += f"## Category: {tag} {self.create_anchor('category-' + self.slugify(tag))}\n\n"
            
            for path_name, path_endpoints in sorted(paths.items()):
                md_content += f"### Path: {path_name} {self.create_anchor('path-' + self.slugify(path_name))}\n\n"
                
                # Sort endpoints by path then method
                sorted_endpoints = sorted(path_endpoints, 
                                         key=lambda e: (e["path"], self.method_order(e["method"])))
                
                for endpoint in sorted_endpoints:
                    md_content += self.format_endpoint(endpoint, models)
                    md_content += "---\n\n"
        
        # Add models section
        if models:
            md_content += "## Data Models {#data-models}\n\n"
            
            for model_name, model_info in sorted(models.items()):
                md_content += self.format_model(model_name, model_info)
                md_content += "---\n\n"
                
        return md_content
    
    def generate_mermaid(self, file_path: str, endpoints: List[Dict[str, Any]],
                     models: Dict[str, Dict[str, Any]]) -> str:
        """
        Generate Mermaid diagram code from extracted endpoints and models for a specific file.
        
        Args:
            file_path: Path to the router file
            endpoints: List of endpoints for the file
            models: Dictionary of models for the file
            
        Returns:
            Generated Mermaid code with enhanced colors and styling
        """
        # Extract title from filepath
        path_parts = Path(file_path).parts
        try:
            # Look for the folder before 'router' in the path
            router_index = path_parts.index('router')
            if router_index > 0:
                title = path_parts[router_index - 1].capitalize()
            else:
                title = "API"
        except ValueError:
            title = "API"

        mermaid_code = "graph LR\n"
        
        # Define color classes
        mermaid_code += "  %% Define styles for different elements\n"
        mermaid_code += "  classDef model fill:#e1d5e7,stroke:#9673a6,stroke-width:2px;\n"
        mermaid_code += "  classDef endpoint fill:#dae8fc,stroke:#6c8ebf,stroke-width:2px;\n"
        mermaid_code += "  classDef get fill:#d5e8d4,stroke:#82b366,stroke-width:2px;\n"
        mermaid_code += "  classDef post fill:#ffe6cc,stroke:#d79b00,stroke-width:2px;\n"
        mermaid_code += "  classDef put fill:#fff2cc,stroke:#d6b656,stroke-width:2px;\n"
        mermaid_code += "  classDef delete fill:#f8cecc,stroke:#b85450,stroke-width:2px;\n"
        mermaid_code += "  classDef field fill:#f5f5f5,stroke:#666666,stroke-width:1px;\n"
        mermaid_code += "  classDef request fill:#e1f5fe,stroke:#4fc3f7,stroke-width:1px;\n"
        mermaid_code += "  classDef response fill:#e8f5e9,stroke:#66bb6a,stroke-width:1px;\n\n"
        
        # Add title and underline
        mermaid_code += f"  subgraph {title} API\n"
        mermaid_code += "    direction TB\n"
        
        # Add models
        for model_name, model_info in models.items():
            mermaid_code += f"    {model_name}[\"{model_name}\"]:::model\n"
            for field_name, field_info in model_info["fields"].items():
                field_type = field_info["type"]
                field_id = f"{model_name}_{field_name}"
                mermaid_code += f"    {field_id}(\"{field_name}: {field_type}\"):::field\n"
                mermaid_code += f"    {model_name} --> {field_id}\n"
        
        # Add endpoints with method-specific colors
        for endpoint in endpoints:
            endpoint_name = f"{endpoint['method']} {endpoint['path']}"
            endpoint_id = endpoint['function']
            
            # Apply different styling based on HTTP method
            method = endpoint['method'].lower()
            if method == "get":
                mermaid_code += f"    {endpoint_id}[\"{endpoint_name}\"]:::get\n"
            elif method == "post":
                mermaid_code += f"    {endpoint_id}[\"{endpoint_name}\"]:::post\n"
            elif method == "put":
                mermaid_code += f"    {endpoint_id}[\"{endpoint_name}\"]:::put\n"
            elif method == "delete":
                mermaid_code += f"    {endpoint_id}[\"{endpoint_name}\"]:::delete\n"
            else:
                mermaid_code += f"    {endpoint_id}[\"{endpoint_name}\"]:::endpoint\n"
            
            # Add request and response models
            if endpoint["request_model"]:
                req_id = f"{endpoint_id}_req"
                mermaid_code += f"    {req_id}(\"{endpoint['request_model']}\"):::request\n"
                mermaid_code += f"    {req_id} --> {endpoint_id}\n"
            
            if endpoint["response_model"]:
                res_id = f"{endpoint_id}_res"
                mermaid_code += f"    {res_id}(\"{endpoint['response_model']}\"):::response\n"
                mermaid_code += f"    {endpoint_id} --> {res_id}\n"
        
        # Close subgraph
        mermaid_code += "  end\n\n"
        
        # Add legend
        mermaid_code += "  subgraph Legend\n"
        mermaid_code += "    model_ex[\"Model\"]:::model\n"
        mermaid_code += "    field_ex(\"Field\"):::field\n"
        mermaid_code += "    get_ex[\"GET\"]:::get\n"
        mermaid_code += "    post_ex[\"POST\"]:::post\n"
        mermaid_code += "    put_ex[\"PUT\"]:::put\n"
        mermaid_code += "    delete_ex[\"DELETE\"]:::delete\n"
        mermaid_code += "    req_ex(\"Request\"):::request\n"
        mermaid_code += "    res_ex(\"Response\"):::response\n"
        mermaid_code += "  end\n"
        
        return mermaid_code
    
    def method_order(self, method: str) -> int:
        """
        Return a number representing the conventional ordering of HTTP methods.
        
        Args:
            method: HTTP method name
            
        Returns:
            Ordering value
        """
        order = {
            "GET": 0,
            "POST": 1,
            "PUT": 2,
            "PATCH": 3,
            "DELETE": 4
        }
        return order.get(method, 99)
    
    def slugify(self, text: str) -> str:
        """
        Convert text to URL-friendly slug.
        
        Args:
            text: Input text
            
        Returns:
            Slugified text
        """
        return re.sub(r'[^\w]+', '-', text.lower()).strip('-')
    
    def create_anchor(self, slug: str) -> str:
        """
        Create an HTML anchor tag for navigation.
        
        Args:
            slug: Anchor identifier
            
        Returns:
            HTML anchor tag
        """
        return f"<a id=\"{slug}\"></a>"
    
    def format_endpoint(self, endpoint: Dict[str, Any], models: Dict[str, Dict[str, Any]]) -> str:
        """
        Format a single endpoint as Markdown.
        
        Args:
            endpoint: Endpoint information
            models: Available models
            
        Returns:
            Formatted Markdown
        """
        md = f"#### {endpoint['method']} {endpoint['path']}\n\n"
        md += f"**Function:** `{endpoint['function']}`\n\n"
        md += f"**Source File:** `{endpoint['source_file']}`\n\n"
        
        if endpoint["tags"]:
            md += "**Tags:** " + ", ".join(f"`{tag}`" for tag in endpoint["tags"]) + "\n\n"
            
        if endpoint["docstring"]:
            md += "**Description:**\n\n"
            md += f"{endpoint['docstring']}\n\n"
            
        if endpoint["request_model"] and endpoint["request_model"] in models:
            md += f"**Request Body:** [`{endpoint['request_model']}`](#model-{self.slugify(endpoint['request_model'])})\n\n"
        elif endpoint["request_model"]:
            md += f"**Request Body:** `{endpoint['request_model']}`\n\n"
            
        if endpoint["response_model"] and endpoint["response_model"] in models:
            md += f"**Response Model:** [`{endpoint['response_model']}`](#model-{self.slugify(endpoint['response_model'])})\n\n"
        elif endpoint["response_model"]:
            md += f"**Response Model:** `{endpoint['response_model']}`\n\n"
            
        # Generate example request
        md += "**Example Request:**\n\n"
        md += "```python\nimport requests\n\n"
        
        # Extract path parameters
        path_params = re.findall(r'{(\w+)}', endpoint['path'])
        
        # Add path parameters section if needed
        if path_params:
            md += "# Path parameters\n"
            for param in path_params:
                md += f"{param} = 'value'  # Replace with actual {param}\n"
            md += "\n"
            
        # Create URL with parameters if needed
        if path_params:
            url_parts = []
            path_parts = endpoint['path'].split('/')
            for part in path_parts:
                if part.startswith('{') and part.endswith('}'):
                    param_name = part[1:-1]
                    url_parts.append(f"{param_name}")
                elif part:
                    url_parts.append(f"'{part}'")
            
            url_str = " + '/' + ".join([p for p in url_parts if p])
            if url_str.startswith("'") and url_str.endswith("'"):
                url_str = url_str[1:-1]
                md += f"url = 'https://localhost:8001/{url_str}'\n\n"
            else:
                md += f"url = 'https://localhost:8001/' + {url_str}\n\n"
        else:
            md += f"url = 'https://localhost:8001{endpoint['path']}'\n\n"
            
        # Add request body for appropriate methods
        if endpoint['method'] in ['POST', 'PUT', 'PATCH'] and endpoint["request_model"]:
            md += "# Request payload\n"
            
            # If model definition is available, generate a more detailed example
            if endpoint["request_model"] in models:
                model_info = models[endpoint["request_model"]]
                md += "payload = {\n"
                for field_name, field_info in model_info["fields"].items():
                    field_type = field_info["type"]
                    # Generate appropriate example value based on type
                    if "str" in field_type.lower():
                        md += f"    '{field_name}': 'example',\n"
                    elif "int" in field_type.lower():
                        md += f"    '{field_name}': 1,\n"
                    elif "float" in field_type.lower():
                        md += f"    '{field_name}': 1.0,\n"
                    elif "bool" in field_type.lower():
                        md += f"    '{field_name}': True,\n"
                    elif "list" in field_type.lower():
                        md += f"    '{field_name}': [],\n"
                    elif "dict" in field_type.lower() or "json" in field_type.lower():
                        md += f"    '{field_name}': {{}},\n"
                    else:
                        md += f"    '{field_name}': None,  # {field_type}\n"
                md += "}\n\n"
            else:
                md += f"payload = {{\n    # Required fields for {endpoint['request_model']}\n}}\n\n"
                
            md += f"response = requests.{endpoint['method'].lower()}(url, json=payload)\n"
        else:
            md += f"response = requests.{endpoint['method'].lower()}(url)\n"
            
        md += "print(response.status_code)\n"
        md += "print(response.json())\n"
        md += "```\n\n"
        
        # Add example response for GET requests with defined response models
        if endpoint['method'] == 'GET' and endpoint["response_model"]:
            md += "**Example Response:**\n\n"
            md += "```json\n"
            
            # If model definition is available, generate a more detailed example
            if endpoint["response_model"] in models:
                model_info = models[endpoint["response_model"]]
                response_example = {}
                
                for field_name, field_info in model_info["fields"].items():
                    field_type = field_info["type"]
                    # Generate appropriate example value based on type
                    if "str" in field_type.lower():
                        response_example[field_name] = "example"
                    elif "int" in field_type.lower():
                        response_example[field_name] = 1
                    elif "float" in field_type.lower():
                        response_example[field_name] = 1.0
                    elif "bool" in field_type.lower():
                        response_example[field_name] = True
                    elif "list" in field_type.lower():
                        response_example[field_name] = []
                    elif "dict" in field_type.lower() or "json" in field_type.lower():
                        response_example[field_name] = {}
                    else:
                        response_example[field_name] = None
                        
                md += json.dumps(response_example, indent=2) + "\n"
            else:
                md += "{\n    // " + endpoint["response_model"] + " structure\n}\n"
                
            md += "```\n\n"
            
        return md
    
    def format_model(self, model_name: str, model_info: Dict[str, Any]) -> str:
        """
        Format a data model as Markdown.
        
        Args:
            model_name: Name of the model
            model_info: Model information
            
        Returns:
            Formatted Markdown
        """
        md = f"### {model_name} {self.create_anchor('model-' + self.slugify(model_name))}\n\n"
        
        if model_info["docstring"]:
            md += f"{model_info['docstring']}\n\n"
            
        md += "**Fields:**\n\n"
        md += "| Field | Type | Required | Description |\n"
        md += "|-------|------|----------|-------------|\n"
        
        for field_name, field_info in sorted(model_info["fields"].items()):
            field_type = field_info["type"]
            required = "Yes" if field_info["default"] is None else "No"
            default = f" (default: `{field_info['default']}`)" if field_info["default"] is not None else ""
            md += f"| `{field_name}` | `{field_type}` | {required} | {default} |\n"
            
        md += "\n**Example:**\n\n"
        md += "```python\nfrom pydantic import BaseModel\n\n"
        md += f"class {model_name}(BaseModel):\n"
        
        for field_name, field_info in sorted(model_info["fields"].items()):
            if field_info["default"] is None:
                md += f"    {field_name}: {field_info['type']}\n"
            else:
                md += f"    {field_name}: {field_info['type']} = {field_info['default']}\n"
                
        md += "```\n\n"
        
        md += "```json\n"
        example = {}
        
        for field_name, field_info in model_info["fields"].items():
            field_type = field_info["type"]
            # Skip fields with a default of None if not required
            if field_info["default"] == "None" and "Optional" in field_type:
                continue
                
            # Generate appropriate example value based on type
            if "str" in field_type.lower():
                example[field_name] = "example"
            elif "int" in field_type.lower():
                example[field_name] = 1
            elif "float" in field_type.lower():
                example[field_name] = 1.0
            elif "bool" in field_type.lower():
                example[field_name] = True
            elif "list" in field_type.lower() or "List" in field_type:
                example[field_name] = []
            elif "dict" in field_type.lower() or "Dict" in field_type:
                example[field_name] = {}
            else:
                # Handle any other type as null
                example[field_name] = None
                
        md += json.dumps(example, indent=2) + "\n"
        md += "```\n\n"
        
        return md
    
    def process_files(self) -> Tuple[str, str, List[str]]:
        """
        Process all router files and generate documentation.
        
        Returns:
            Tuple of (markdown_path, json_path, mermaid_paths) where documentation was saved
        """
        router_files = self.find_router_files()
        
        if not router_files:
            self.log("No router files found in project.")
            return None, None, []
            
        all_endpoints = {}
        all_models = {}
        mermaid_paths = []
        
        # Process each file
        for file_path in router_files:
            endpoints = self.extract_endpoints(file_path)
            models = self.extract_models(file_path)
            
            if endpoints:
                all_endpoints[file_path] = endpoints
                
            if models:
                all_models[file_path] = models
                
            # Generate mermaid diagram for each file
            mermaid_content = self.generate_mermaid(file_path, endpoints, models)
            
            # Save mermaid file
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            mermaid_path = os.path.join(self.output_path, f"{file_name}_diagram.mmd")
            with open(mermaid_path, 'w', encoding='utf-8') as mermaid_file:
                mermaid_file.write(mermaid_content)
                
            self.log(f"Mermaid diagram saved to: {mermaid_path}")
            mermaid_paths.append(mermaid_path)
                
        # Generate documentation if endpoints were found
        if all_endpoints:
            # Generate markdown
            md_content = self.generate_markdown(all_endpoints, all_models)
            
            # Save markdown file
            md_path = os.path.join(self.output_path, "API_Documentation.md")
            with open(md_path, 'w', encoding='utf-8') as md_file:
                md_file.write(md_content)
                
            self.log(f"Markdown documentation saved to: {md_path}")
            
            # Save JSON for potential further processing
            all_data = {
                "endpoints": all_endpoints,
                "models": all_models
            }
            json_path = os.path.join(self.output_path, "api_data.json")
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(all_data, json_file, indent=2)
                
            self.log(f"JSON data saved to: {json_path}")
            
            return md_path, json_path, mermaid_paths
        else:
            self.log("No endpoints found in any of the router files.")
            return None, None, []
    
    def generate_summary(self, md_path: str, json_path: str, mermaid_paths: List[str]) -> None:
        """
        Generate a summary of the API documentation.
        
        Args:
            md_path: Path to the generated markdown file
            json_path: Path to the generated JSON data
            mermaid_paths: List of paths to the generated mermaid files
        """
        if not (md_path and json_path and mermaid_paths):
            print("No documentation generated.")
            return
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            endpoint_count = sum(len(endpoints) for endpoints in data["endpoints"].values())
            file_count = len(data["endpoints"])
            model_count = sum(len(models) for models in data["models"].values())
            
            # Count by method
            methods = {}
            for file_path, endpoints in data["endpoints"].items():
                for endpoint in endpoints:
                    method = endpoint["method"]
                    methods[method] = methods.get(method, 0) + 1
                    
            # Count by tag
            tags = {}
            for file_path, endpoints in data["endpoints"].items():
                for endpoint in endpoints:
                    for tag in endpoint["tags"]:
                        tags[tag] = tags.get(tag, 0) + 1
                        
            print("\n" + "="*50)
            print("API DOCUMENTATION SUMMARY")
            print("="*50)
            print(f"Total endpoints: {endpoint_count}")
            print(f"Router files: {file_count}")
            print(f"Data models: {model_count}")
            
            print("\nEndpoints by method:")
            for method, count in sorted(methods.items()):
                print(f"  {method}: {count}")
                
            if tags:
                print("\nEndpoints by tag:")
                for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {tag}: {count}")
                    
            print("\nDocumentation files:")
            print(f"  Markdown: {md_path}")
            print(f"  JSON: {json_path}")
            print(f"  Mermaid diagrams:")
            for mermaid_path in mermaid_paths:
                print(f"    - {mermaid_path}")
            print("="*50)
            
        except Exception as e:
            print(f"Error generating summary: {str(e)}")


def doc_generator():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate API documentation from FastAPI router files")
    parser.add_argument("--path", default=".", help="Path to the project root directory")
    parser.add_argument("--output", help="Path where documentation will be saved")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    generator = RouterDocsGenerator(
        project_path=args.path,
        output_path=args.output,
        verbose=args.verbose
    )
    
    md_path, json_path, mermaid_paths = generator.process_files()
    generator.generate_summary(md_path, json_path, mermaid_paths)


if __name__ == "__main__":
    doc_generator()