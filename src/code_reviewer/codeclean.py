from src.code_reviewer.codeanalysis import CodeQualityAnalyzer

def analyze_code_quality(root_directory, output_directory="code_quality_reports"):
    """
    Analyze code quality in the given directory.
    
    Args:
        root_directory: Directory containing code to analyze
        output_directory: Directory where reports will be written
        
    Returns:
        Dict with analysis results
    """
    analyzer = CodeQualityAnalyzer(root_directory, output_directory)
    return analyzer.analyze_all()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze code quality for production readiness")
    parser.add_argument("directory", help="The directory to analyze")
    parser.add_argument("--output", "-o", default="code_quality_reports", 
                        help="Directory where reports should be saved")
    
    args = parser.parse_args()
    
    print(f"Analyzing code in {args.directory}...")
    results = analyze_code_quality(args.directory, args.output)
    
    # Print summary
    total_issues = sum(len(issues) for issues in results.values())
    print(f"Analysis complete. Found {total_issues} issues in {len(results)} files.")
    print(f"Reports saved to {args.output}/")
    print(f"Final report available at {args.output}/final_report.md")