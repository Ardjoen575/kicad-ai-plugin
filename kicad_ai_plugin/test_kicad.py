"""
Test script for KiCad file extraction functionality
"""
import os
import sys
import logging
from kicad_file_processor import is_kicad_file, extract_kicad_file_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_kicad_file(filepath):
    """Test KiCad file handling with a specified file"""
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} does not exist.")
        return False
        
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Check if this is a KiCad file
    if not is_kicad_file(file_ext):
        print(f"Error: {filename} is not a KiCad file.")
        return False
        
    print(f"Processing KiCad file: {filename} ({filesize} bytes)")
    print(f"File extension: {file_ext}")
    
    try:
        # Read the file
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Extract KiCad file info
        info = extract_kicad_file_info(filepath, file_ext, content)
        
        # Display the results
        print("\nKiCad File Information:")
        print(f"File type: {info.get('file_type', 'Unknown')}")
        
        for key, value in info.items():
            if key not in ['file_type', 'summary']:
                print(f"{key}: {value}")
                
        print(f"\nSummary: {info.get('summary', 'No summary available')}")
        
        return True
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return False
        

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        test_kicad_file(filepath)
    else:
        print("Usage: python test_kicad.py <path_to_kicad_file>")
        # Try to find KiCad files in the current directory
        kicad_files = []
        for filename in os.listdir('.'):
            if os.path.isfile(filename):
                ext = os.path.splitext(filename)[1].lower()
                if is_kicad_file(ext):
                    kicad_files.append(filename)
        
        if kicad_files:
            print("\nKiCad files found in the current directory:")
            for filename in kicad_files:
                print(f"  - {filename}")
            print("\nRun the script with one of these files as an argument.") 