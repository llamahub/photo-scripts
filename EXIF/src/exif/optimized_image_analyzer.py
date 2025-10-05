import os
import csv
import json
import subprocess
import concurrent.futures
from pathlib import Path
from .image_data import ImageData


class OptimizedImageAnalyzer(ImageData):
    """High-performance image analyzer with batch processing and parallel execution."""
    
    def __init__(self, folder_path=None, csv_output=None, max_workers=None, batch_size=100):
        """Initialize OptimizedImageAnalyzer with performance tuning options.
        
        Args:
            folder_path: Path to analyze
            csv_output: CSV output path
            max_workers: Number of parallel workers (default: CPU count)
            batch_size: Number of files to process in each ExifTool batch
        """
        self.folder_path = folder_path
        self.csv_output = csv_output
        self.results = []
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.batch_size = batch_size

    def analyze_images_fast(self, folder_path=None, progress_callback=None):
        """High-performance image analysis with batch ExifTool calls and parallel processing.
        
        Args:
            folder_path: Path to analyze
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of analysis results
        """
        if folder_path is None:
            folder_path = self.folder_path
        
        if not folder_path:
            raise ValueError("No folder path provided")
            
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Find all image files
        image_files = self._find_image_files_fast(folder_path)
        
        if not image_files:
            return []
        
        print(f"Found {len(image_files)} images to analyze...")
        
        # Process in batches with parallel execution
        self.results = []
        total_files = len(image_files)
        
        for i in range(0, total_files, self.batch_size):
            batch = image_files[i:i + self.batch_size]
            batch_results = self._process_batch_parallel(batch)
            self.results.extend(batch_results)
            
            if progress_callback:
                progress = min(i + self.batch_size, total_files)
                progress_callback(progress, total_files)
            else:
                print(f"Processed {min(i + self.batch_size, total_files)}/{total_files} images...")
        
        return self.results

    def _find_image_files_fast(self, folder_path):
        """Fast image file discovery using pathlib."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.raw', '.cr2', '.nef', '.orf', '.raf', '.rw2'}
        image_files = []
        
        # Use pathlib for faster directory traversal
        path = Path(folder_path)
        for ext in image_extensions:
            # Use glob patterns for each extension (case insensitive)
            image_files.extend(path.rglob(f'*{ext}'))
            image_files.extend(path.rglob(f'*{ext.upper()}'))
        
        return [str(f) for f in image_files]

    def _process_batch_parallel(self, file_batch):
        """Process a batch of files with parallel ExifTool calls and analysis."""
        # Step 1: Batch ExifTool extraction for all files
        exif_data = self._batch_extract_exif(file_batch)
        
        # Step 2: Parallel analysis using the cached EXIF data
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._analyze_single_image_cached, filepath, exif_data.get(filepath, {})): filepath
                for filepath in file_batch
            }
            
            results = []
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    filepath = future_to_file[future]
                    results.append({
                        'filepath': filepath,
                        'filename': os.path.basename(filepath),
                        'error': str(e),
                        'condition_category': 'Error'
                    })
            
            return results

    def _batch_extract_exif(self, file_batch):
        """Extract EXIF data for multiple files in a single ExifTool call."""
        if not file_batch:
            return {}
        
        try:
            # Single ExifTool call for entire batch
            cmd = [
                "exiftool",
                "-j",
                "-DateTimeOriginal",
                "-ExifIFD:DateTimeOriginal", 
                "-XMP-photoshop:DateCreated",
                "-FileModifyDate",
                "-FileTypeExtension",
                "-ImageWidth",
                "-ImageHeight"
            ] + file_batch
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data_list = json.loads(result.stdout)
                # Create filepath -> exif_data mapping
                exif_map = {}
                for item in data_list:
                    source_file = item.get('SourceFile', '')
                    if source_file:
                        exif_map[source_file] = item
                return exif_map
            
        except Exception as e:
            print(f"Batch EXIF extraction failed: {e}")
        
        return {}

    def _analyze_single_image_cached(self, filepath, exif_data):
        """Analyze single image using pre-extracted EXIF data."""
        try:
            filename = os.path.basename(filepath)
            parent_name = self.getParentName(filepath)
            
            # Use cached EXIF data instead of calling get_exif
            image_date = self._getImageDate_cached(filepath, exif_data)
            filename_date = self.getFilenameDate(filepath)
            parent_date = self.normalize_parent_date(parent_name)
            
            # Fast date processing
            alt_filename_date = self.extract_alt_filename_date(filepath, parent_date)
            parent_date_norm = self.strip_time(parent_date)
            filename_date_norm = self.strip_time(filename_date)
            image_date_norm = self.strip_time(image_date)
            
            condition_desc, condition_category = self.get_condition(
                parent_date_norm, filename_date_norm, image_date_norm
            )
            
            # Extract dimensions and extension from cached EXIF
            true_ext = exif_data.get("FileTypeExtension", Path(filepath).suffix.lstrip(".")).lower()
            width = str(exif_data.get("ImageWidth", ""))
            height = str(exif_data.get("ImageHeight", ""))
            
            target_filename = self.getTargetFilename(filepath, "/tmp")
            
            return {
                'filepath': filepath,
                'filename': filename,
                'parent_name': parent_name,
                'parent_date': parent_date,
                'filename_date': filename_date,
                'image_date': image_date,
                'alt_filename_date': alt_filename_date,
                'parent_date_norm': parent_date_norm,
                'filename_date_norm': filename_date_norm,
                'image_date_norm': image_date_norm,
                'condition_desc': condition_desc,
                'condition_category': condition_category,
                'true_ext': true_ext,
                'width': width,
                'height': height,
                'target_filename': os.path.basename(target_filename)
            }
            
        except Exception as e:
            return {
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'error': str(e),
                'condition_category': 'Error'
            }

    def _getImageDate_cached(self, filepath, exif_data):
        """Get image date using cached EXIF data."""
        import re
        
        # Check EXIF fields in priority order
        for key in [
            "DateTimeOriginal",
            "ExifIFD:DateTimeOriginal",
            "XMP-photoshop:DateCreated",
            "FileModifyDate",
        ]:
            if key in exif_data and exif_data[key]:
                dt = exif_data[key]
                dt = re.sub(
                    r"^(\d{4})[:_-](\d{2})[:_-](\d{2})[ T_]?(\d{2})?:?(\d{2})?:?(\d{2})?",
                    r"\1-\2-\3 \4:\5:\6",
                    dt,
                )
                return self.normalize_date(dt)

        # Fallback to filename date
        filename_date = self.getFilenameDate(filepath)
        if filename_date != "1900-01-01 00:00":
            return filename_date

        return "1900-01-01 00:00"

    def analyze_with_progress(self, folder_path=None):
        """Analyze with progress reporting."""
        def progress_callback(current, total):
            percentage = (current / total) * 100
            print(f"Progress: {current}/{total} ({percentage:.1f}%)")
        
        return self.analyze_images_fast(folder_path, progress_callback)

    def analyze_sample(self, folder_path=None, sample_size=100):
        """Analyze a random sample for quick overview."""
        import random
        
        if folder_path is None:
            folder_path = self.folder_path
        
        image_files = self._find_image_files_fast(folder_path)
        
        if len(image_files) <= sample_size:
            return self.analyze_images_fast(folder_path)
        
        # Random sample
        sample_files = random.sample(image_files, sample_size)
        print(f"Analyzing sample of {sample_size} images from {len(image_files)} total...")
        
        batch_results = self._process_batch_parallel(sample_files)
        self.results = batch_results
        return batch_results

    # Inherit all other methods from ImageAnalyzer
    def save_to_csv(self, csv_path=None, results=None):
        """Save analysis results to CSV file."""
        if csv_path is None:
            csv_path = self.csv_output
            
        if results is None:
            results = self.results
            
        if not csv_path:
            raise ValueError("No CSV output path provided")
            
        if not results:
            raise ValueError("No results to save")
            
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        headers = [
            'filepath', 'filename', 'parent_name', 'parent_date', 'filename_date', 
            'image_date', 'alt_filename_date', 'parent_date_norm', 'filename_date_norm', 
            'image_date_norm', 'condition_desc', 'condition_category', 'true_ext', 
            'width', 'height', 'target_filename', 'error'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for result in results:
                row = {header: result.get(header, '') for header in headers}
                writer.writerow(row)

    def get_statistics(self, results=None):
        """Get statistics about the analysis results."""
        if results is None:
            results = self.results
            
        if not results:
            return {}
            
        total_images = len(results)
        categories = {}
        errors = 0
        
        for result in results:
            if 'error' in result:
                errors += 1
                continue
                
            category = result.get('condition_category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        
        stats = {
            'total_images': total_images,
            'successful_analyses': total_images - errors,
            'errors': errors,
            'categories': categories
        }
        
        if total_images > 0:
            stats['category_percentages'] = {
                cat: round((count / total_images) * 100, 2) 
                for cat, count in categories.items()
            }
        
        return stats

    def print_statistics(self, results=None):
        """Print analysis statistics to console."""
        stats = self.get_statistics(results)
        
        if not stats:
            print("No analysis results available")
            return
            
        print(f"\nAnalysis Statistics:")
        print(f"Total images: {stats['total_images']}")
        print(f"Successful analyses: {stats['successful_analyses']}")
        
        if stats['errors'] > 0:
            print(f"Errors: {stats['errors']}")
        
        print(f"\nCondition Categories:")
        for category, count in stats['categories'].items():
            percentage = stats['category_percentages'].get(category, 0)
            print(f"  {category}: {count} ({percentage}%)")