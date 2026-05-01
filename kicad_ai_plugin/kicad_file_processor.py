import re
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_kicad_mime_type(extension):
    """Get the MIME type for a KiCad file extension"""
    mime_map = {
        '.kicad_pcb': 'application/x-kicad-pcb',
        '.kicad_sch': 'application/x-kicad-sch',
        '.kicad_pro': 'application/x-kicad-project',
        '.kicad_mod': 'application/x-kicad-footprint',
        '.kicad_sym': 'application/x-kicad-symbol',
        '.kicad_wks': 'application/x-kicad-worksheet',
        '.net': 'application/x-kicad-netlist',
        '.lib': 'application/x-kicad-library'
    }
    
    ext = extension.lower()
    return mime_map.get(ext, 'application/octet-stream')

def is_kicad_file(file_ext):
    """Check if this is a KiCad file based on extension"""
    return file_ext.lower() in [
        '.kicad_pcb', '.kicad_sch', '.kicad_pro', '.net', 
        '.lib', '.kicad_mod', '.kicad_wks', '.kicad_sym'
    ]

def extract_kicad_file_info(filepath, file_ext, content):
    """Extract relevant information from KiCad files"""
    try:
        info = {}
        
        # Process based on file type
        if file_ext == '.kicad_pcb':
            # Extract PCB information
            info["file_type"] = "KiCad PCB Layout"
            
            # Count number of layers
            layers_match = re.search(r'\(layers\s+([^)]+)\)', content)
            if layers_match:
                layers_text = layers_match.group(1)
                layers_count = len(re.findall(r'\([0-9]+\s+"[^"]+"\s+[^)]+\)', layers_text))
                info["layers_count"] = layers_count
            
            # Count footprints
            footprints_count = content.count('(footprint ')
            info["footprints_count"] = footprints_count
            
            # Extract board dimensions if available
            edge_cuts_pattern = r'\(gr_rect\s+\(start\s+([\d\.-]+)\s+([\d\.-]+)\)\s+\(end\s+([\d\.-]+)\s+([\d\.-]+)\)'
            edge_matches = re.findall(edge_cuts_pattern, content)
            if edge_matches:
                for match in edge_matches:
                    x1, y1, x2, y2 = map(float, match)
                    width = abs(x2 - x1)
                    height = abs(y2 - y1)
                    if "dimensions" not in info:
                        info["dimensions"] = []
                    info["dimensions"].append(f"{width:.2f}mm x {height:.2f}mm")
            
        elif file_ext == '.kicad_sch':
            # Extract schematic information
            info["file_type"] = "KiCad Schematic"
            
            # Count symbols (components)
            symbols_count = content.count('(symbol ')
            info["symbols_count"] = symbols_count
            
            # Check if JSON-based format (KiCad 6+)
            if content.lstrip().startswith('{'):
                try:
                    sch_data = json.loads(content)
                    if "sheets" in sch_data:
                        info["sheets_count"] = len(sch_data["sheets"])
                except Exception as e:
                    logger.error(f"Error parsing schematic JSON: {str(e)}")
            else:
                # S-expression format - count sheets
                sheets_count = content.count('(sheet ')
                info["sheets_count"] = sheets_count
            
        elif file_ext == '.kicad_pro':
            # Extract project information
            info["file_type"] = "KiCad Project"
            
            # Try to parse as JSON (KiCad 6+)
            try:
                project_data = json.loads(content)
                
                # Extract version
                if "version" in project_data:
                    info["kicad_version"] = project_data["version"]
                
                # Extract nets count if available
                if "board" in project_data and "design_settings" in project_data["board"]:
                    settings = project_data["board"]["design_settings"]
                    if "rules" in settings and "netclass_patterns" in settings["rules"]:
                        info["netclasses"] = len(settings["rules"]["netclass_patterns"])
            except Exception as e:
                logger.error(f"Error parsing project JSON: {str(e)}")
            
        elif file_ext == '.net':
            # Extract netlist information
            info["file_type"] = "KiCad Netlist"
            
            # Count components and nets
            components_count = content.count('(comp ')
            info["components_count"] = components_count
            
            nets_count = content.count('(net ')
            info["nets_count"] = nets_count
            
        elif file_ext == '.lib' or file_ext == '.kicad_sym':
            # Extract library information
            info["file_type"] = "KiCad Symbol Library"
            
            # Count symbols in the library
            if file_ext == '.kicad_sym':
                symbols_count = content.count('(symbol ')
                info["symbols_count"] = symbols_count
            else:
                # Older .lib format
                symbols_count = content.count('DEF ')
                info["symbols_count"] = symbols_count
            
        elif file_ext == '.kicad_mod':
            # Extract module information
            info["file_type"] = "KiCad Footprint"
            
            # Try to get the footprint name
            name_match = re.search(r'\(footprint\s+"([^"]+)"', content)
            if name_match:
                info["footprint_name"] = name_match.group(1)
            
            # Count pads
            pads_count = content.count('(pad ')
            info["pads_count"] = pads_count
            
        # Add a summary string that can be included in the prompt
        summary_parts = []
        for key, value in info.items():
            if key != "file_type":  # Skip file_type as it's added first
                summary_parts.append(f"{key}: {value}")
                
        info["summary"] = f"{info.get('file_type', 'KiCad File')}: " + ", ".join(summary_parts)
        
        return info
        
    except Exception as e:
        logger.error(f"Error extracting KiCad file info: {str(e)}")
        return {"error": f"Could not extract KiCad file information: {str(e)}"}

def process_kicad_file(filepath):
    """Process a KiCad file and extract information"""
    import os
    
    # Get file info
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Check if this is a KiCad file
    if not is_kicad_file(file_ext):
        return {"error": "Not a KiCad file"}
    
    # Prepare file data
    file_data = {
        "name": filename,
        "path": filepath,
        "type": get_kicad_mime_type(file_ext),
        "size": filesize,
        "is_binary": False,  # KiCad files are treated as text
        "mime_type": get_kicad_mime_type(file_ext),
        "is_kicad_file": True,
        "kicad_file_type": file_ext[1:]  # Store the KiCad file type without the dot
    }
    
    try:
        # Read the file content
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            text_content = f.read()
            file_data["content"] = text_content
            
            # For API compatibility, also add a content preview
            content_preview = text_content[:4000]
            if len(text_content) > 4000:
                content_preview += "...(truncated)"
            file_data["content_preview"] = content_preview
            
            # Extract KiCad specific information
            file_data["kicad_info"] = extract_kicad_file_info(filepath, file_ext, text_content)
            
        return file_data
        
    except Exception as e:
        logger.error(f"Error processing KiCad file: {str(e)}")
        return {"error": f"Error processing KiCad file: {str(e)}"}

# Test function
def test_kicad_file_processor(filepath):
    """Test the KiCad file processor with a given file"""
    result = process_kicad_file(filepath)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    print(f"Successfully processed KiCad file: {result['name']}")
    print(f"Type: {result['kicad_file_type']}")
    print(f"Size: {result['size']} bytes")
    
    if "kicad_info" in result:
        print("\nKiCad File Information:")
        for key, value in result["kicad_info"].items():
            if key != "content" and key != "content_preview":
                print(f"  {key}: {value}")
    
    print("\nContent Preview:")
    preview_lines = result.get("content_preview", "").split("\n")[:10]
    for line in preview_lines:
        print(f"  {line[:80]}")
    print("  ...")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_kicad_file_processor(sys.argv[1])
    else:
        print("Usage: python kicad_file_processor.py <path_to_kicad_file>") 