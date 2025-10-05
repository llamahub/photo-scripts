import os
import csv
from pathlib import Path
from .image_data import ImageData


class ImageAnalyzer:
    def __init__(self, folder_path=None, csv_output=None):
        """Initialize ImageAnalyzer with optional folder path and CSV output path."""
        self.folder_path = folder_path
        self.csv_output = csv_output
        self.results = []

    def analyze_images(self, folder_path=None):
        """Analyze all images in the specified folder and return detailed information.
        
        Args:
            folder_path: Path to analyze (uses instance folder_path if not provided)
            
        Returns:
            List of dictionaries containing analysis results for each image
        """
        if folder_path is None:
            folder_path = self.folder_path
        
        if not folder_path:
            raise ValueError("No folder path provided")
            
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")
            
        self.results = []
        
        # Get list of image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.raw', '.cr2', '.nef', '.orf', '.raf', '.rw2'}
        image_files = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    image_files.append(os.path.join(root, file))
        
        # Analyze each image
        for filepath in image_files:
            result = self._analyze_single_image(filepath)
            self.results.append(result)
            
        return self.results
    
    def _analyze_single_image(self, filepath):
        """Analyze a single image file and return detailed information."""
        try:
            # Get basic file info
            filename = os.path.basename(filepath)
            parent_name = ImageData.getParentName(filepath)
            
            # Get dates from different sources
            image_date = ImageData.getImageDate(filepath)
            filename_date = ImageData.getFilenameDate(filepath)
            parent_date = ImageData.normalize_parent_date(parent_name)
            
            # Extract alternative filename date if available
            alt_filename_date = ImageData.extract_alt_filename_date(filepath, parent_date)
            
            # Normalize dates for comparison
            parent_date_norm = ImageData.strip_time(parent_date)
            filename_date_norm = ImageData.strip_time(filename_date)
            image_date_norm = ImageData.strip_time(image_date)
            
            # Get condition analysis
            condition_desc, condition_category = ImageData.get_condition(
                parent_date_norm, filename_date_norm, image_date_norm
            )
            
            # Get image properties
            true_ext = ImageData.getTrueExt(filepath)
            width, height = ImageData.getImageSize(filepath)
            
            # Generate target filename for comparison
            target_filename = ImageData.getTargetFilename(filepath, "/tmp")  # Use temp root for analysis
            
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
    
    def save_to_csv(self, csv_path=None, results=None):
        """Save analysis results to CSV file.
        
        Args:
            csv_path: Path to save CSV (uses instance csv_output if not provided)
            results: Results to save (uses instance results if not provided)
        """
        if csv_path is None:
            csv_path = self.csv_output
            
        if results is None:
            results = self.results
            
        if not csv_path:
            raise ValueError("No CSV output path provided")
            
        if not results:
            raise ValueError("No results to save")
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # Define CSV headers
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
                # Ensure all headers are present with empty string defaults
                row = {header: result.get(header, '') for header in headers}
                writer.writerow(row)
    
    def get_statistics(self, results=None):
        """Get statistics about the analysis results.
        
        Args:
            results: Results to analyze (uses instance results if not provided)
            
        Returns:
            Dictionary containing analysis statistics
        """
        if results is None:
            results = self.results
            
        if not results:
            return {}
            
        total_images = len(results)
        categories = {}
        errors = 0
        
        # Count condition categories
        for result in results:
            if 'error' in result:
                errors += 1
                continue
                
            category = result.get('condition_category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        
        # Calculate percentages
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
        """Print analysis statistics to console.
        
        Args:
            results: Results to analyze (uses instance results if not provided)
        """
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