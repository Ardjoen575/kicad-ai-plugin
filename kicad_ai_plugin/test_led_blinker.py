#!/usr/bin/env python3
"""
Test script to generate an LED blinker circuit using the KiCadProjectGenerator.
"""

import os
import logging
from kicad_project_generator import KiCadProjectGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Create a test output directory
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "led_blinker_test")
    os.makedirs(test_dir, exist_ok=True)
    
    # Initialize the generator
    generator = KiCadProjectGenerator(output_dir=test_dir)
    
    # Set project name
    generator.set_project_name("led_blinker_circuit")
    
    # Create a description for an LED blinker circuit
    description = """
    Design a basic LED blinker circuit on a custom PCB. 
    The circuit should include a 555 timer IC configured in astable mode to generate a blinking signal, 
    driving an LED. Include appropriate decoupling capacitors and a current-limiting resistor for the LED. 
    Design a compact PCB layout for this circuit with proper labeling of components and a 2-pin header for power supply connection.
    """
    
    # Process the description and generate the project
    success, message, files = generator.generate_complete_project(description, "led_blinker_circuit")
    
    logger.info(f"Project generation: {success}, {message}")
    logger.info(f"Generated files: {files}")
    
    # Try to open the PCB file
    if success:
        pcb_path = files.get('pcb', '')
        if pcb_path:
            logger.info(f"Attempting to open PCB file: {pcb_path}")
            # This will use the macOS 'open' command which should work
            open_success, open_message = generator.open_pcb_editor()
            logger.info(f"Open PCB result: {open_success}, {open_message}")

if __name__ == "__main__":
    main() 