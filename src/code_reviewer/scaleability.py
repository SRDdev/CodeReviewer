import ast


class ScalabilityVisitor(ast.NodeVisitor):
    """Visit AST nodes to check for scalability issues."""
    
    def __init__(self):
        self.hardcoded_configs = []  # (line, name)
        self.resource_issues = []  # (resource_type, line)
        self.potential_bottlenecks = []  # (bottleneck_type, line, code)
        self.in_with_context = False
    
    def visit_Assign(self, node):
        """Visit an assignment node."""
        # Check for hardcoded configuration values
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                
                # Check if this looks like a config constant
                if (name.isupper() and 
                    isinstance(node.value, (ast.Str, ast.Num, ast.List, ast.Dict)) and
                    not self.in_with_context):
                    
                    self.hardcoded_configs.append((node.lineno, name))
        
        # Visit children
        self.generic_visit(node)
    
    def visit_With(self, node):
        """Visit a with-statement node."""
        old_with_context = self.in_with_context
        self.in_with_context = True
        
        # Visit children
        self.generic_visit(node)
        
        self.in_with_context = old_with_context
    
    def visit_Call(self, node):
        """Visit a function call node."""
        func = node.func
        
        # Check for resource management
        if isinstance(func, ast.Name):
            if func.id == 'open' and not self.in_with_context:
                self.resource_issues.append(("file", node.lineno))
        
        # Check for bottlenecks: large data processing without pagination/streaming
        if isinstance(func, ast.Attribute):
            if hasattr(func.value, 'id'):
                # SQL queries without limits
                if (func.attr in ['execute', 'executemany'] and 
                    len(node.args) > 0 and 
                    isinstance(node.args[0], ast.Str) and 
                    'SELECT' in node.args[0].s.upper() and 
                    'LIMIT' not in node.args[0].s.upper()):
                    
                    self.potential_bottlenecks.append((
                        "SQL query",
                        node.lineno,
                        "SQL query without LIMIT clause"
                    ))
        
        # Visit children
        self.generic_visit(node)
        
    def visit_For(self, node):
        """Visit a for-loop node."""
        # Check for inefficient iteration
        if isinstance(node.iter, ast.Call):
            func = node.iter.func
            if isinstance(func, ast.Name) and func.id == 'range' and len(node.iter.args) > 0:
                if isinstance(node.iter.args[0], ast.Num) and node.iter.args[0].n > 1000:
                    self.potential_bottlenecks.append((
                        "Computational",
                        node.lineno,
                        f"Large range loop (n={node.iter.args[0].n})"
                    ))
        
        # Visit children
        self.generic_visit(node)
