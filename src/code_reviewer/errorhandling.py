import ast


class ErrorHandlingVisitor(ast.NodeVisitor):
    """Visit AST nodes to check for error handling issues."""
    
    def __init__(self):
        self.functions_without_try_except = []
        self.bare_except_lines = []
        self.io_without_error_handling = []
        self.current_function = None
        self.in_try_except = False
        
    def visit_FunctionDef(self, node):
        """Visit a function definition node."""
        old_function = self.current_function
        old_try_except = self.in_try_except
        
        self.current_function = node.name
        self.in_try_except = False
        
        # Visit all statements inside the function
        for child in node.body:
            self.visit(child)
        
        # If no try-except was found in the function and it's not a simple getter/setter
        if not self.in_try_except and len(node.body) > 1:
            self.functions_without_try_except.append((node.name, node.lineno))
        
        self.current_function = old_function
        self.in_try_except = old_try_except
    
    def visit_Try(self, node):
        """Visit a try-except block."""
        old_try_except = self.in_try_except
        self.in_try_except = True
        
        # Check for bare except clauses
        for handler in node.handlers:
            if handler.type is None:
                self.bare_except_lines.append(handler.lineno)
        
        # Visit children
        self.generic_visit(node)
        self.in_try_except = old_try_except
    
    def visit_Call(self, node):
        """Visit a function call node."""
        # Check for IO operations without error handling
        func = node.func
        
        # Check if it's a file operation
        if (isinstance(func, ast.Attribute) and func.attr in ['open', 'read', 'write', 'close'] or
            (isinstance(func, ast.Name) and func.id == 'open')):
            
            if not self.in_try_except:
                # Get the operation name
                if isinstance(func, ast.Attribute):
                    operation = f"{self._get_source_segment(func)}"
                else:
                    operation = "open"
                
                self.io_without_error_handling.append((node.lineno, operation))
        
        self.generic_visit(node)
    
    def _get_source_segment(self, node):
        """Get the source representation of a node if possible."""
        if hasattr(node, 'value') and hasattr(node, 'attr'):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
        return "unknown operation"
