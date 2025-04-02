import ast


class ComplexityVisitor(ast.NodeVisitor):
    """Visit AST nodes to compute complexity metrics."""
    
    def __init__(self):
        self.file_complexity = 0
        self.functions = []  # (name, complexity)
        self.functions_count = 0
        self.classes_count = 0
        self.avg_function_complexity = 0
        self.max_function_complexity = 0
    
    def visit_ClassDef(self, node):
        """Visit a class definition node."""
        self.classes_count += 1
        self.file_complexity += 1
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Visit a function definition node."""
        self.functions_count += 1
        
        # Calculate cyclomatic complexity
        complexity = 1  # Base complexity
        
        for child_node in ast.walk(node):
            if isinstance(child_node, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child_node, ast.Try):
                complexity += len(child_node.handlers)
            elif isinstance(child_node, ast.BoolOp) and isinstance(child_node.op, ast.And):
                complexity += len(child_node.values) - 1
        
        self.functions.append((node.name, complexity))
        self.file_complexity += complexity
        
        if complexity > self.max_function_complexity:
            self.max_function_complexity = complexity
        
        # Visit children
        self.generic_visit(node)
    
    def finalize(self):
        """Calculate final metrics after visiting all nodes."""
        if self.functions:
            self.avg_function_complexity = sum(c for _, c in self.functions) / len(self.functions)
        return self.file_complexity
