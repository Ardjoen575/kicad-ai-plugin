#!/usr/bin/env python3
"""
Test script to check file generation formats for KiCad files.
"""

import os
import logging
from kicad_project_generator import KiCadProjectGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Create a test output directory
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
    os.makedirs(test_dir, exist_ok=True)
    
    # Initialize the generator
    generator = KiCadProjectGenerator(output_dir=test_dir)
    
    # Set project name
    generator.set_project_name("test_project")
    
    # Create a simple circuit description
    description = "Create a simple LED with a resistor"
    
    # Process the description
    success, message = generator.process_description(description)
    logger.info(f"Process description: {success}, {message}")
    
    # Generate each file individually and check format
    
    # 1. Schematic file
    sch_content = generator._generate_schematic_content()
    logger.info(f"Schematic content type: {type(sch_content)}")
    logger.info(f"Schematic content starts with: {sch_content[:100]}")
    
    with open(os.path.join(test_dir, "test_schematic.kicad_sch"), "w") as f:
        f.write(sch_content)
    
    # 2. PCB file
    pcb_content = generator._generate_pcb_content()
    logger.info(f"PCB content type: {type(pcb_content)}")
    logger.info(f"PCB content starts with: {pcb_content[:100]}")
    
    with open(os.path.join(test_dir, "test_pcb.kicad_pcb"), "w") as f:
        f.write(pcb_content)
    
    # 3. Project file
    pro_content = generator._generate_project_content()
    logger.info(f"Project content type: {type(pro_content)}")
    logger.info(f"Project content starts with: {pro_content[:100]}")
    
    with open(os.path.join(test_dir, "test_project.kicad_pro"), "w") as f:
        f.write(pro_content)
    
    # 4. Netlist file
    net_content = generator._generate_netlist_content()
    logger.info(f"Netlist content type: {type(net_content)}")
    logger.info(f"Netlist content starts with: {net_content[:100]}")
    
    with open(os.path.join(test_dir, "test_netlist.net"), "w") as f:
        f.write(net_content)
        
    logger.info(f"All test files were written to: {test_dir}")
    
    # Also test the complete project generation
    success, message, files = generator.generate_complete_project(description, "complete_test")
    logger.info(f"Complete project: {success}, {message}")
    logger.info(f"Generated files: {files}")

if __name__ == "__main__":
    main() 