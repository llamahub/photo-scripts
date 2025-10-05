#!/usr/bin/env python3

import argparse
import sys
import os
import csv
from datetime import datetime

# Import from our exif module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from exif import ImageAnalyzer, ImageData


def main():
    parser = argparse.ArgumentParser(description="Analyze image organization and date consistency.")
    parser.add_argument("--source", required=True, help="Source root folder to analyze")
    parser.add_argument("--target", required=True, help="Target root folder for comparison")
    parser.add_argument("--label", default="", help="Label for target filenames (optional)")
    parser.add_argument("--output", help="CSV output file path (default: .log/analyze_YYYY-MM-DD_HHMM.csv)")
    parser.add_argument("--no-stats", action="store_true", help="Don't print statistics to console")
    
    args = parser.parse_args()
    
    # Validate source folder
    if not os.path.exists(args.source):
        print(f"Error: Source folder not found: {args.source}")
        sys.exit(1)
    
    # Determine output file path
    if args.output:
        csv_path = args.output
    else:
        now = datetime.now().strftime("%Y-%m-%d_%H%M")
        log_dir = ".log"
        os.makedirs(log_dir, exist_ok=True)
        csv_path = os.path.join(log_dir, f"analyze_{now}.csv")
    
    print(f"Analyzing images in: {args.source}")
    print(f"Output CSV: {csv_path}")
    
    try:
        # Create analyzer and perform analysis
        analyzer = ImageAnalyzer(folder_path=args.source, csv_output=csv_path)
        results = analyzer.analyze_images()
        
        # Generate target filename and target exists info for each result
        for result in results:
            if 'error' not in result:
                source_path = result['filepath']
                target_path = ImageData.getTargetFilename(source_path, args.target, args.label)
                target_exists = os.path.exists(target_path)
                
                # Add target information to result
                result['target_path'] = target_path
                result['target_exists'] = "TRUE" if target_exists else "FALSE"
        
        # Save to CSV with custom format to match original
        save_custom_csv(csv_path, results)
        
        print(f"Analysis complete! Results written to: {csv_path}")
        print(f"Analyzed {len(results)} images")
        
        # Print statistics unless disabled
        if not args.no_stats:
            analyzer.print_statistics(results)
            
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)


def save_custom_csv(csv_path, results):
    """Save results in the original CSV format for compatibility."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    with open(csv_path, "w", newline="", encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header matching original format
        writer.writerow([
            "Condition", "Status", "Parent Date", "Filename Date", "Image Date", 
            "Source Path", "Target Path", "Target Exists", "Alt Filename Date"
        ])
        
        # Write data rows
        for result in results:
            if 'error' in result:
                # Handle error cases
                writer.writerow([
                    "Error", "Error", "", "", "", 
                    result['filepath'], "", "FALSE", result.get('error', '')
                ])
            else:
                writer.writerow([
                    result.get('condition_desc', ''),
                    result.get('condition_category', ''),
                    result.get('parent_date_norm', ''),
                    result.get('filename_date_norm', ''),
                    result.get('image_date_norm', ''),
                    result.get('filepath', ''),
                    result.get('target_path', ''),
                    result.get('target_exists', 'FALSE'),
                    result.get('alt_filename_date', '')
                ])


if __name__ == "__main__":
    main()
