import ast


class CodeQualityVisitor(ast.NodeVisitor):
    """Visit AST nodes to check for code quality issues."""
    
    def __init__(self):
        self.long_functions = []  # (name, line, length)
        self.complex_functions = []  # (name, line, complexity)
        self.missing_docstrings = []  # (type, name, line)
        self.possibly_unused_imports = []  # (name, line)
        self.imports = set()
        self.used_names = set()
    
    def visit_FunctionDef(self, node):
        """Visit a function definition node."""
        # Check for docstring
        if not ast.get_docstring(node):
            self.missing_docstrings.append(("Function", node.name, node.lineno))
        
        # Count lines in function
        function_lines = sum(1 for _ in ast.walk(node)) - 1  # Approximation
        if function_lines > 30:
            self.long_functions.append((node.name, node.lineno, function_lines))
        
        # Calculate cyclomatic complexity (approximation)
        complexity = 1  # Base complexity
        
        for child_node in ast.walk(node):
            if isinstance(child_node, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child_node, ast.Try):
                complexity += len(child_node.handlers)
            elif isinstance(child_node, ast.BoolOp) and isinstance(child_node.op, ast.And):
                complexity += len(child_node.values) - 1
        
        if complexity > 10:
            self.complex_functions.append((node.name, node.lineno, complexity))
        
        # Visit children
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Visit a class definition node."""
        # Check for docstring
        if not ast.get_docstring(node):
            self.missing_docstrings.append(("Class", node.name, node.lineno))
        
        # Visit children
        self.generic_visit(node)
    
    def visit_Module(self, node):
        """Visit a module node."""
        # Check for module docstring
        if not ast.get_docstring(node):
            self.missing_docstrings.append(("Module", "module", 1))
        
        # Visit children
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Record imports."""
        for name in node.names:
            self.imports.add(name.name.split('.')[0])
            self.possibly_unused_imports.append((name.name, node.lineno))
    
    def visit_ImportFrom(self, node):
        """Record from-imports."""
        if node.module:
            module_name = node.module.split('.')[0]
            self.imports.add(module_name)
            
            for name in node.names:
                if name.name != '*':
                    self.possibly_unused_imports.append((f"{module_name}.{name.name}", node.lineno))
    
    def visit_Name(self, node):
        """Record name usage."""
        # Add to used names
        self.used_names.add(node.id)
        
        # Visit children
        self.generic_visit(node)
