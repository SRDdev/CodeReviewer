from src.code_reviewer.codeclean import analyze_code_quality
from src.docs_generator.doc_generator import doc_generator
import argparse
from src.docs_generator.doc_generator import RouterDocsGenerator

def main():
    # Take inputs from the user
    code_path = input("Enter the path to the code file to analyze: ")
    project_path = input("Enter the path to the project root directory for documentation generation: ")
    output_path = input("Enter the path where documentation will be saved: ")
    verbose_input = input("Enable verbose output? (yes/no): ")
    verbose = verbose_input.lower() in ["yes", "y"]

    # Analyze code quality
    quality_report = analyze_code_quality(code_path, output_directory="docs/codereview")
    print("Code Quality Report:")
    print(quality_report)

    # Generate documentation
    generator = RouterDocsGenerator(
        project_path=project_path,
        output_path=output_path,
        verbose=verbose
    )
    
    md_path, json_path, mermaid_paths = generator.process_files()
    generator.generate_summary(md_path, json_path, mermaid_paths)
    print(f"Documentation generated and saved to {output_path}")

if __name__ == "__main__":
    main()
