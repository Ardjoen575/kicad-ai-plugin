import os
import json
import re
import logging
import tempfile
import datetime
import uuid
import subprocess
import sys
from typing import Dict, List, Tuple, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KiCadProjectGenerator:
    """
    Generates complete KiCad project files from natural language descriptions.
    
    This class creates:
    - Schematic files (.kicad_sch)
    - PCB layout files (.kicad_pcb)
    - Project files (.kicad_pro)
    - Netlist files (.net)
    
    With automatic update support for existing projects.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the KiCad project generator.
        
        Args:
            output_dir: Directory where project files will be saved. Defaults to a temp directory.
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        self.project_name = "ai_generated_project"
        
        # Initialize component and connection lists
        self.components = []
        self.connections = []
        self.uuid_map = {}
        
        # Initialize component libraries dictionary for KiCad 9.0
        self.component_libraries = {
            'resistor': 'Device:R',
            'capacitor': 'Device:C',
            'inductor': 'Device:L',
            'diode': 'Device:D',
            'led': 'Device:LED',
            'transistor': 'Device:Q_NPN_BCE',
            'mosfet': 'Device:Q_NMOS_GDS',
            'opamp': 'Amplifier_Operational:LM741',
            'microcontroller': 'MCU_Microchip_ATmega:ATmega328P-PU',
            'voltage_regulator': 'Regulator_Linear:LM7805_TO220',
            'crystal': 'Device:Crystal',
            'connector': 'Connector:Conn_01x04_Pin',
            'switch': 'Switch:SW_Push',
            'potentiometer': 'Device:R_Potentiometer',
            'relay': 'Relay:SANYOU_SRD_Form_C',
            'fuse': 'Device:Fuse',
            'speaker': 'Device:Speaker',
            'battery': 'Device:Battery',
            'sensor': 'Sensor:DHT11',
            'ic': 'Device:IC',
        }
        
        # Initialize component footprints dictionary for KiCad 9.0
        self.component_footprints = {
            'resistor': 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
            'capacitor': 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
            'inductor': 'Inductor_THT:L_Axial_L5.3mm_D2.2mm_P10.16mm_Horizontal_Vishay_IM-1',
            'diode': 'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal',
            'led': 'LED_THT:LED_D5.0mm',
            'transistor': 'Package_TO_SOT_THT:TO-92_Inline',
            'mosfet': 'Package_TO_SOT_THT:TO-220-3_Vertical',
            'opamp': 'Package_DIP:DIP-8_W7.62mm',
            'microcontroller': 'Package_DIP:DIP-28_W7.62mm',
            'voltage_regulator': 'Package_TO_SOT_THT:TO-220-3_Vertical',
            'crystal': 'Crystal:Crystal_HC49-4H_Vertical',
            'connector': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
            'switch': 'Button_Switch_THT:SW_PUSH_6mm',
            'potentiometer': 'Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical',
            'relay': 'Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C',
            'fuse': 'Fuse:Fuse_Blade_ATO_directSolder',
            'speaker': 'Speaker:Speaker_CUI_CMT-1102-76mm',
            'battery': 'Battery:BatteryHolder_Keystone_1058_1x2032',
            'sensor': 'Sensor:Aosong_DHT11_5.5x12.0mm_P2.54mm',
            'ic': 'Package_DIP:DIP-16_W7.62mm',
        }
        
        # Track current components for project
        self.existing_project = False
        self.existing_files = {}
        
    def set_project_name(self, name: str) -> None:
        """Set the name of the project (will be used for filenames)."""
        # Clean the name to make it suitable for a filename
        if not name:
            self.project_name = "ai_kicad_project"
            return
            
        # Remove quotes and command prefixes
        name = name.replace('"', '').replace("'", "")
        name = name.strip()
        
        # If name contains words like "project" or "rename to", extract the actual name
        if " as " in name.lower():
            parts = name.lower().split(" as ")
            name = parts[-1].strip()
        elif " to " in name.lower():
            parts = name.lower().split(" to ")
            name = parts[-1].strip()
            
        # Replace spaces with underscores, but keep other characters
        cleaned_name = name.replace(' ', '_')
        
        # Remove any non-alphanumeric characters except underscores and hyphens
        cleaned_name = re.sub(r'[^\w\-]', '', cleaned_name)
        
        # Ensure name doesn't start with a number
        if cleaned_name and cleaned_name[0].isdigit():
            cleaned_name = "ai_" + cleaned_name
            
        # If name is empty after cleaning, use default
        if not cleaned_name:
            cleaned_name = "ai_kicad_project"
            
        self.project_name = cleaned_name
        
    def rename_project(self, new_name: str) -> Tuple[bool, str, Dict[str, str]]:
        """
        Rename an existing project.
        
        Args:
            new_name: New name for the project
            
        Returns:
            Tuple of (success, message, dict of updated files)
        """
        if not self.existing_project:
            return False, "No existing project loaded to rename", {}
            
        # Store original project information
        original_name = self.project_name
        original_files = {
            'schematic': os.path.join(self.output_dir, f"{original_name}.kicad_sch"),
            'pcb': os.path.join(self.output_dir, f"{original_name}.kicad_pcb"),
            'project': os.path.join(self.output_dir, f"{original_name}.kicad_pro"),
            'netlist': os.path.join(self.output_dir, f"{original_name}.net"),
        }
        
        # Set the new project name
        self.set_project_name(new_name)
        new_files = {}
        
        try:
            # Rename each file
            for file_type, original_path in original_files.items():
                if os.path.exists(original_path):
                    new_path = os.path.join(self.output_dir, f"{self.project_name}.{file_type.split('.')[-1]}")
                    
                    # If file with new name already exists, delete it
                    if os.path.exists(new_path):
                        os.remove(new_path)
                        
                    # Rename the file
                    os.rename(original_path, new_path)
                    new_files[file_type] = new_path
                    
                    # For project file, we need to update the contents too
                    if file_type == 'project':
                        with open(new_path, 'r') as f:
                            content = f.read()
                        
                        # Replace old project name with new one
                        content = content.replace(original_name, self.project_name)
                        
                        with open(new_path, 'w') as f:
                            f.write(content)
            
            return True, f"Successfully renamed project from '{original_name}' to '{self.project_name}'", new_files
            
        except Exception as e:
            logger.error(f"Error renaming project: {str(e)}")
            # Try to revert to original name
            self.project_name = original_name
            return False, f"Error renaming project: {str(e)}", {}
    
    def _generate_uuid(self) -> str:
        """Generate a UUID in KiCad format."""
        return str(uuid.uuid4()).upper()
    
    def _parse_component_value(self, component_type: str, value_str: str) -> str:
        """Parse and normalize component values."""
        if not value_str:
            # Default values if none specified
            if component_type == 'resistor':
                return "10k"
            elif component_type == 'capacitor':
                return "10uF"
            else:
                return ""
                
        # Clean and normalize the value string
        # For future: implement more sophisticated parsing of units
        return value_str.strip()
    
    def process_description(self, description: str) -> Tuple[bool, str]:
        """
        Process a natural language description and extract components and connections.
        
        Args:
            description: Natural language description of the circuit
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Reset current components and connections
            self.components = []
            self.connections = []
            
            # Check for common circuit types
            desc_lower = description.lower()
            
            # Noise Filter (NF)
            if "nf filter" in desc_lower or "noise filter" in desc_lower:
                # Create components for a basic NF (noise filter) circuit
                inductor = {
                    'type': 'inductor',
                    'value': '10uH',
                    'reference': 'L1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 100, 'y': 100},
                }
                
                capacitor1 = {
                    'type': 'capacitor',
                    'value': '100nF',
                    'reference': 'C1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 150, 'y': 100},
                }
                
                resistor = {
                    'type': 'resistor',
                    'value': '50Ω',
                    'reference': 'R1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 200, 'y': 100},
                }
                
                # Add components
                self.components.extend([inductor, capacitor1, resistor])
                
                # Add connections
                self.connections.append({
                    'from': 'L1',
                    'to': 'C1',
                    'net_name': 'Net-L1-C1',
                    'uuid': self._generate_uuid(),
                })
                
                self.connections.append({
                    'from': 'C1',
                    'to': 'R1',
                    'net_name': 'Net-C1-R1',
                    'uuid': self._generate_uuid(),
                })
                
                return True, f"Created NF filter circuit with {len(self.components)} components"
                
            # Low-Pass Filter (LPF)
            elif "lpf" in desc_lower or "low pass" in desc_lower or "low-pass" in desc_lower:
                resistor = {
                    'type': 'resistor',
                    'value': '10k',
                    'reference': 'R1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 100, 'y': 100},
                }
                
                capacitor = {
                    'type': 'capacitor',
                    'value': '100nF',
                    'reference': 'C1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 150, 'y': 100},
                }
                
                # Add components
                self.components.extend([resistor, capacitor])
                
                # Add connections
                self.connections.append({
                    'from': 'R1',
                    'to': 'C1',
                    'net_name': 'Net-R1-C1',
                    'uuid': self._generate_uuid(),
                })
                
                return True, f"Created low-pass filter circuit with {len(self.components)} components"
                
            # High-Pass Filter (HPF)
            elif "hpf" in desc_lower or "high pass" in desc_lower or "high-pass" in desc_lower:
                capacitor = {
                    'type': 'capacitor',
                    'value': '100nF',
                    'reference': 'C1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 100, 'y': 100},
                }
                
                resistor = {
                    'type': 'resistor',
                    'value': '10k',
                    'reference': 'R1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 150, 'y': 100},
                }
                
                # Add components
                self.components.extend([capacitor, resistor])
                
                # Add connections
                self.connections.append({
                    'from': 'C1',
                    'to': 'R1',
                    'net_name': 'Net-C1-R1',
                    'uuid': self._generate_uuid(),
                })
                
                return True, f"Created high-pass filter circuit with {len(self.components)} components"
                
            # Band-Pass Filter (BPF)
            elif "bpf" in desc_lower or "band pass" in desc_lower or "band-pass" in desc_lower:
                capacitor1 = {
                    'type': 'capacitor',
                    'value': '100nF',
                    'reference': 'C1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 100, 'y': 100},
                }
                
                resistor = {
                    'type': 'resistor',
                    'value': '10k',
                    'reference': 'R1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 150, 'y': 100},
                }
                
                capacitor2 = {
                    'type': 'capacitor',
                    'value': '10nF',
                    'reference': 'C2',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 200, 'y': 100},
                }
                
                # Add components
                self.components.extend([capacitor1, resistor, capacitor2])
                
                # Add connections
                self.connections.append({
                    'from': 'C1',
                    'to': 'R1',
                    'net_name': 'Net-C1-R1',
                    'uuid': self._generate_uuid(),
                })
                
                self.connections.append({
                    'from': 'R1',
                    'to': 'C2',
                    'net_name': 'Net-R1-C2',
                    'uuid': self._generate_uuid(),
                })
                
                return True, f"Created band-pass filter circuit with {len(self.components)} components"
                
            # Regular extraction for other descriptions
            self._extract_components(description)
            self._extract_connections(description)
            
            # If we couldn't extract any components, create a simple circuit
            if not self.components:
                # Create a simple circuit with a resistor and capacitor
                resistor = {
                    'type': 'resistor',
                    'value': '10k',
                    'reference': 'R1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 100, 'y': 100},
                }
                
                capacitor = {
                    'type': 'capacitor',
                    'value': '100nF',
                    'reference': 'C1',
                    'uuid': self._generate_uuid(),
                    'position': {'x': 150, 'y': 100},
                }
                
                # Add components
                self.components.extend([resistor, capacitor])
                
                # Add connections
                self.connections.append({
                    'from': 'R1',
                    'to': 'C1',
                    'net_name': 'Net-R1-C1',
                    'uuid': self._generate_uuid(),
                })
                
                return True, f"Created simple circuit with {len(self.components)} components (fallback)"
            
            return True, f"Extracted {len(self.components)} components and {len(self.connections)} connections"
        
        except Exception as e:
            logger.error(f"Error processing description: {str(e)}")
            return False, f"Error processing description: {str(e)}"
    
    def _extract_components(self, description: str) -> None:
        """
        Extract components from a natural language description.
        
        Args:
            description: Natural language description of the circuit
        """
        # Dictionary of component patterns
        component_patterns = {
            'resistor': r'(?:(\d+(?:\.\d+)?)\s*([kKMmGg])?(?:ohm|Ω|ohms)?\s+)?resistors?',
            'capacitor': r'(?:(\d+(?:\.\d+)?)\s*([pPnNuUmM][fF])?)\s+capacitors?',
            'inductor': r'(?:(\d+(?:\.\d+)?)\s*([uUmM][hH])?)\s+inductors?',
            'diode': r'diodes?',
            'led': r'LEDs?',
            'transistor': r'(?:(NPN|PNP))?\s*transistors?',
            'mosfet': r'(?:(N-channel|P-channel))?\s*MOSFETs?',
            'opamp': r'(?:op[- ]amps?|operational amplifiers?)',
            'microcontroller': r'(?:(ATmega\d+|Arduino|ESP\d+|PIC\d+|STM\d+))?\s*microcontrollers?',
            'voltage_regulator': r'(?:(\d+(?:\.\d+)?[vV])?\s*voltage regulators?|LM\d+|LDO)',
            'crystal': r'(?:(\d+(?:\.\d+)?)\s*([kKMmG][hH][zZ])?\s*)?(?:crystals?|oscillators?)',
            'connector': r'(?:(\d+)[- ]pin)?\s*connectors?',
            'switch': r'(?:(SPST|SPDT|DPST|DPDT))?\s*switchs?',
            'potentiometer': r'(?:(\d+(?:\.\d+)?)\s*([kKMm])?(?:ohm|Ω)?)\s*(?:potentiometers?|pots?)',
            'relay': r'(?:(SPST|SPDT|DPST|DPDT))?\s*relays?',
            'fuse': r'(?:(\d+(?:\.\d+)?)\s*([mMA])?\s*)?fuses?',
            'speaker': r'speakers?',
            'battery': r'(?:(\d+(?:\.\d+)?)\s*([vV])?\s*)?(?:batteries?|cells?)',
            'sensor': r'(?:(temperature|humidity|pressure|light|motion|proximity))?\s*sensors?',
            'ic': r'(?:ICs?|integrated circuits?)'
        }
        
        # Dictionary to track how many of each component we've found
        component_counts = {
            'resistor': 1,
            'capacitor': 1,
            'inductor': 1,
            'diode': 1,
            'led': 1,
            'transistor': 1,
            'mosfet': 1,
            'opamp': 1,
            'microcontroller': 1,
            'voltage_regulator': 1,
            'crystal': 1,
            'connector': 1,
            'switch': 1,
            'potentiometer': 1,
            'relay': 1,
            'fuse': 1,
            'speaker': 1,
            'battery': 1,
            'sensor': 1,
            'ic': 1
        }
        
        # Find all component mentions
        for comp_type, pattern in component_patterns.items():
            # Search for the component pattern in the description
            matches = re.finditer(pattern, description, re.IGNORECASE)
            
            for match in matches:
                count = 1  # Default to 1 component
                
                # Check if a quantity is specified before the component
                qty_match = re.search(r'(\d+)\s+' + pattern, description)
                if qty_match:
                    count = int(qty_match.group(1))
                
                # Create the specified number of components
                for i in range(count):
                    # Get component value from regex groups if available
                    value = self._extract_component_value(match, comp_type)
                    
                    # Create reference designator (R1, C1, etc.)
                    ref_prefix = self._get_ref_prefix(comp_type)
                    reference = f"{ref_prefix}{component_counts[comp_type]}"
                    component_counts[comp_type] += 1
                    
                    # Generate a position (simplified for now)
                    x_pos = 100 + (len(self.components) % 5) * 100
                    y_pos = 100 + (len(self.components) // 5) * 100
                    
                    # Create the component object
                    component = {
                        'type': comp_type,
                        'value': value,
                        'reference': reference,
                        'uuid': self._generate_uuid(),
                        'position': {'x': x_pos, 'y': y_pos}
                    }
                    
                    # Add to the components list
                    self.components.append(component)
                    
                    # Store UUID for connections
                    self.uuid_map[reference] = component['uuid']
    
    def _extract_component_value(self, match, comp_type: str) -> str:
        """Extract component value from a regex match."""
        if not match.groups():
            # Default values if no specific value was provided
            default_values = {
                'resistor': '10k',
                'capacitor': '100nF',
                'inductor': '10uH',
                'diode': '1N4148',
                'led': 'RED',
                'transistor': '2N2222',
                'mosfet': '2N7000',
                'opamp': 'LM741',
                'microcontroller': 'ATmega328P',
                'voltage_regulator': 'LM7805',
                'crystal': '16MHz',
                'connector': 'Conn_01x04',
                'switch': 'SW_Push',
                'potentiometer': '10k',
                'relay': 'SPDT',
                'fuse': '500mA',
                'speaker': '8Ω',
                'battery': '9V',
                'sensor': 'Temperature',
                'ic': 'IC'
            }
            return default_values.get(comp_type, '')
        
        # Try to extract the value from the match groups
        try:
            if comp_type == 'resistor':
                value = match.group(1) or '10'
                unit = match.group(2) or ''
                return f"{value}{unit}"
            elif comp_type == 'capacitor':
                value = match.group(1) or '100'
                unit = match.group(2) or 'nF'
                return f"{value}{unit}"
            elif comp_type == 'inductor':
                value = match.group(1) or '10'
                unit = match.group(2) or 'uH'
                return f"{value}{unit}"
            elif comp_type == 'transistor':
                return match.group(1) or '2N2222'
            elif comp_type == 'mosfet':
                return match.group(1) or '2N7000'
            elif comp_type == 'microcontroller':
                return match.group(1) or 'ATmega328P'
            elif comp_type == 'voltage_regulator':
                return match.group(1) or 'LM7805'
            elif comp_type == 'crystal':
                value = match.group(1) or '16'
                unit = match.group(2) or 'MHz'
                return f"{value}{unit}"
            elif comp_type == 'connector':
                pins = match.group(1) or '4'
                return f"Conn_01x{pins}"
            elif comp_type == 'switch':
                return match.group(1) or 'SPST'
            elif comp_type == 'potentiometer':
                value = match.group(1) or '10'
                unit = match.group(2) or 'k'
                return f"{value}{unit}"
            elif comp_type == 'relay':
                return match.group(1) or 'SPDT'
            elif comp_type == 'fuse':
                value = match.group(1) or '500'
                unit = match.group(2) or 'mA'
                return f"{value}{unit}"
            elif comp_type == 'battery':
                value = match.group(1) or '9'
                unit = match.group(2) or 'V'
                return f"{value}{unit}"
            elif comp_type == 'sensor':
                return match.group(1) or 'Temperature'
            else:
                # For other component types, return a default value
                return comp_type.capitalize()
        except (IndexError, AttributeError):
            # If we can't extract a value, return a default
            return comp_type.capitalize()
    
    def _get_ref_prefix(self, component_type: str) -> str:
        """Get the reference prefix for a component type."""
        # Default reference prefixes for common components
        prefix_map = {
            'resistor': 'R',
            'capacitor': 'C',
            'inductor': 'L',
            'diode': 'D',
            'led': 'LED',
            'transistor': 'Q',
            'mosfet': 'Q',
            'opamp': 'U',
            'microcontroller': 'U',
            'voltage_regulator': 'U',
            'crystal': 'Y',
            'connector': 'J',
            'switch': 'SW',
            'potentiometer': 'RV',
            'relay': 'K',
            'fuse': 'F',
            'speaker': 'LS',
            'battery': 'BT',
            'sensor': 'U',
            'ic': 'U',
        }
        
        return prefix_map.get(component_type, 'U')
    
    def _extract_connections(self, description: str) -> None:
        """Extract connections from natural language description."""
        # Simple pattern for connections
        connection_pattern = r'connect\s+([A-Z][A-Z0-9]*)\s+(?:to|and)\s+([A-Z][A-Z0-9]*)'
        
        # Find all connections
        matches = re.finditer(connection_pattern, description, re.IGNORECASE)
        
        # Process connections
        for match in matches:
            from_ref = match.group(1).upper()
            to_ref = match.group(2).upper()
            
            # Add to connections list
            self.connections.append({
                'from': from_ref,
                'to': to_ref,
                'net_name': f"Net-{from_ref}-{to_ref}",
                'uuid': self._generate_uuid(),
            })
    
    def generate_schematic_file(self) -> Tuple[bool, str, str]:
        """
        Generate a KiCad schematic file (.kicad_sch).
        
        Returns:
            Tuple of (success, message, file_path)
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Path for the schematic file
            schematic_path = os.path.join(self.output_dir, f"{self.project_name}.kicad_sch")
            
            # Generate the schematic content
            schematic_content = self._generate_schematic_content()
            
            # Write to file
            with open(schematic_path, 'w') as f:
                f.write(schematic_content)
                
            return True, f"Schematic file created at {schematic_path}", schematic_path
            
        except Exception as e:
            logger.error(f"Error generating schematic file: {str(e)}")
            return False, f"Error generating schematic file: {str(e)}", ""
    
    def _generate_schematic_content(self) -> str:
        """Generate the content for the KiCad schematic file in S-expression format."""
        # Create a simplified but valid KiCad 9.0 schematic file
        uuid_main = self._generate_uuid()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Start with basic file structure (based on KiCad 9.0 format)
        content = f"""(kicad_sch (version 20230121) (generator "KiCadProjectGenerator")

  (uuid {uuid_main})
  (paper "A4")
  (title_block
    (title "{self.project_name}")
    (date "{timestamp.split()[0]}")
    (rev "v1.0")
    (company "AI Generated")
  )

  (lib_symbols
"""
        
        # Add library symbols
        for comp_type in set(comp["type"] for comp in self.components):
            if comp_type in self.component_libraries:
                lib_id = self.component_libraries[comp_type]
                lib_name, part_name = lib_id.split(':')
                symbol_uuid = self._generate_uuid()
                content += f"""    (symbol "{lib_id}"
      (pin_numbers hide) (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
      (property "Reference" "{self._get_ref_prefix(comp_type)}" (id 0) (at 0 1.27 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "{part_name}" (id 1) (at 0 -2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (id 2) (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "" (id 3) (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "{part_name}_1_1"
        (rectangle (start -3.81 2.54) (end 3.81 -2.54)
          (stroke (width 0.254) (type default) (color 0 0 0 0))
          (fill (type background))
        )
        (pin passive line (at -6.35 0 0) (length 2.54)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 6.35 0 180) (length 2.54)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
"""
        content += "  )\n\n"
        
        # Add components (symbols) section
        content += "  (symbols\n"
        for i, comp in enumerate(self.components):
            x_pos = 100 + (i % 5) * 100
            y_pos = 100 + (i // 5) * 100
            lib_id = self.component_libraries.get(comp["type"], "Device:Unknown")
            content += f"""    (symbol (lib_id "{lib_id}") (at {x_pos} {y_pos} 0) (unit 1)
      (in_bom yes) (on_board yes) (fields_autoplaced)
      (uuid {comp["uuid"]})
      (property "Reference" "{comp["reference"]}" (id 0) (at {x_pos} {y_pos-12.7} 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "{comp["value"]}" (id 1) (at {x_pos} {y_pos+12.7} 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "{self.component_footprints.get(comp["type"], "")}" (id 2) (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "" (id 3) (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
    )
"""
        content += "  )\n\n"
        
        # Add wires/connections
        if self.connections:
            for conn in self.connections:
                from_ref = conn["from"]
                to_ref = conn["to"]
                
                # Find the components by reference
                from_comp = next((c for c in self.components if c["reference"] == from_ref), None)
                to_comp = next((c for c in self.components if c["reference"] == to_ref), None)
                
                if from_comp and to_comp:
                    # Get component positions
                    from_x = from_comp["position"]["x"] + 10  # Add offset for pin
                    from_y = from_comp["position"]["y"]
                    to_x = to_comp["position"]["x"] - 10  # Add offset for pin
                    to_y = to_comp["position"]["y"]
                    
                    content += f"""  (wire (pts (xy {from_x} {from_y}) (xy {to_x} {to_y}))
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid {conn["uuid"]})
  )
"""
        
        # Add required bitmap section (empty but required)
        content += "  (bitmap (at 0 0) (scale 1)\n  )\n\n"
        
        # Add required junction section (empty but required)
        content += "  (junction (at 0 0) (diameter 0) (color 0 0 0 0)\n    (uuid 00000000-0000-0000-0000-000000000000)\n  )\n\n"
        
        # Add no_connect section (empty but required)
        content += "  (no_connect (at 0 0) (uuid 00000000-0000-0000-0000-000000000000)\n  )\n\n"
        
        # Add text section (empty but required)
        content += "  (text \"\" (at 0 0 0)\n    (effects (font (size 1.27 1.27)) (justify left bottom))\n    (uuid 00000000-0000-0000-0000-000000000000)\n  )\n\n"
        
        # Add label section (empty but required)
        content += "  (label \"\" (at 0 0 0)\n    (effects (font (size 1.27 1.27)) (justify left bottom))\n    (uuid 00000000-0000-0000-0000-000000000000)\n  )\n\n"
        
        # Add global_label section (empty but required)
        content += "  (global_label \"\" (at 0 0 0) (fields_autoplaced)\n    (effects (font (size 1.27 1.27)) (justify left))\n    (uuid 00000000-0000-0000-0000-000000000000)\n    (property \"Intersheet References\" \"\" (id 0) (at 0 0 0)\n      (effects (font (size 1.27 1.27)) hide)\n    )\n  )\n\n"
        
        # Add hierarchical_label section (empty but required)
        content += "  (hierarchical_label \"\" (at 0 0 0) (fields_autoplaced)\n    (effects (font (size 1.27 1.27)) (justify left))\n    (uuid 00000000-0000-0000-0000-000000000000)\n  )\n\n"
        
        # Add sheet instances section
        content += "  (sheet_instances\n"
        content += f"    (path \"/\" (page \"1\"))\n"
        content += "  )\n"
        
        # Add symbol instances section (required)
        content += "  (symbol_instances\n"
        for comp in self.components:
            content += f"    (\"{comp['uuid']}\" (value \"{comp['value']}\") (unit 1) (in_bom yes) (on_board yes))\n"
        content += "  )\n"
        
        # Close the main kicad_sch element
        content += ")\n"
        
        return content
    
    def generate_pcb_file(self) -> Tuple[bool, str, str]:
        """
        Generate a KiCad PCB file (.kicad_pcb).
        
        Returns:
            Tuple of (success, message, file_path)
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Path for the PCB file
            pcb_path = os.path.join(self.output_dir, f"{self.project_name}.kicad_pcb")
            
            # Generate the PCB content
            pcb_content = self._generate_pcb_content()
            
            # Write to file
            with open(pcb_path, 'w') as f:
                f.write(pcb_content)
                
            return True, f"PCB file created at {pcb_path}", pcb_path
            
        except Exception as e:
            logger.error(f"Error generating PCB file: {str(e)}")
            return False, f"Error generating PCB file: {str(e)}", ""
    
    def _generate_pcb_content(self) -> str:
        """Generate the content for the KiCad PCB file."""
        # Helper function to find net number for a component pad
        def find_net_for_component(ref, pad_num):
            # For simplicity, assign connections to pad 1 and GND to pad 2
            if pad_num == 1:
                for i, conn in enumerate(self.connections):
                    if conn["from"] == ref or conn["to"] == ref:
                        return i + 1
            return 0  # Default to GND
        
        # Create a KiCad 9.0 PCB file with all required elements
        pcb_content = f"""(kicad_pcb (version 20231120) (generator "AI KiCad Project Generator")

  (general
    (thickness 1.6)
    (drawings 5)
    (tracks 0)
    (zones 0)
    (modules {len(self.components)})
    (nets {len(self.connections) + 1})
  )

  (paper "A4")
  (title_block
    (title "{self.project_name}")
    (date "{datetime.datetime.now().strftime('%Y-%m-%d')}")
    (rev "v1.0")
    (company "AI Generated")
  )

  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
    (50 "User.1" user)
    (51 "User.2" user)
    (52 "User.3" user)
    (53 "User.4" user)
    (54 "User.5" user)
    (55 "User.6" user)
    (56 "User.7" user)
    (57 "User.8" user)
    (58 "User.9" user)
  )

  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
    )
    (pad_to_mask_clearance 0.05)
    (solder_mask_min_width 0.25)
    (aux_axis_origin 0 0)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros false)
      (usegerberextensions false)
      (usegerberattributes true)
      (usegerberadvancedattributes true)
      (creategerberjobfile true)
      (dashed_line_dash_ratio 12.000000)
      (dashed_line_gap_ratio 3.000000)
      (svgprecision 4)
      (plotframeref false)
      (viasonmask false)
      (mode 1)
      (useauxorigin false)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (dxfpolygonmode true)
      (dxfimperialunits true)
      (dxfusepcbnew false)
      (psnegative false)
      (psa4output false)
      (plotreference true)
      (plotvalue true)
      (plotinvisibletext false)
      (sketchpadsonfab false)
      (subtractmaskfromsilk false)
      (outputformat 1)
      (mirror false)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "")
    )
  )
"""
        
        # Add net definitions
        pcb_content += "\n  (net 0 \"GND\")\n"
        
        # Add nets for connections
        for i, conn in enumerate(self.connections):
            net_num = i + 1
            pcb_content += f'  (net {net_num} "{conn["net_name"]}")\n'
        
        # Add edge cuts (board outline) - a simple rectangle
        pcb_content += """
  (gr_rect (start 50 50) (end 150 150) (layer "Edge.Cuts") (width 0.1) (fill none) (tstamp 00000000-0000-0000-0000-000000000001))
  (gr_text "AI Generated" (at 100 175 0) (layer "F.SilkS") (tstamp 00000000-0000-0000-0000-000000000005)
    (effects (font (size 1.5 1.5) (thickness 0.3)) (justify left))
  )
"""

        # Add footprints for components
        for i, comp in enumerate(self.components):
            x_pos = 70 + (i % 3) * 30  # Arrange in rows of 3
            y_pos = 70 + (i // 3) * 30
            
            # Get footprint for the component
            footprint_id = self.component_footprints.get(comp["type"], "")
            if not footprint_id:
                continue
                
            # Extract library and footprint name
            parts = footprint_id.split(':')
            if len(parts) != 2:
                continue
                
            lib_name, fp_name = parts
            
            # Add footprint in S-expression format with corrected syntax for KiCad 9.0
            # Notice the added "effects" attribute in property elements
            pcb_content += f"""
  (footprint "{footprint_id}" (layer "F.Cu") (tstamp {comp["uuid"]})
    (at {x_pos} {y_pos})
    (property "Reference" "{comp["reference"]}" (id 0) (at {x_pos} {y_pos-5} 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Value" "{comp["value"]}" (id 1) (at {x_pos} {y_pos+5} 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Footprint" "{footprint_id}" (id 2) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "" (id 3) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (pad 1 thru_hole circle (at -2.54 0) (size 1.7 1.7) (drill 1) (layers *.Cu *.Mask) (net {find_net_for_component(comp["reference"], 1)}))
    (pad 2 thru_hole circle (at 2.54 0) (size 1.7 1.7) (drill 1) (layers *.Cu *.Mask) (net {find_net_for_component(comp["reference"], 2)}))
  )
"""
        
        # Close the PCB file
        pcb_content += ")\n"
        
        return pcb_content
    
    def generate_project_file(self) -> Tuple[bool, str, str]:
        """
        Generate a KiCad project file (.kicad_pro).
        
        Returns:
            Tuple of (success, message, file_path)
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Path for the project file
            project_path = os.path.join(self.output_dir, f"{self.project_name}.kicad_pro")
            
            # Generate the project content
            project_content = self._generate_project_content()
            
            # Write to file
            with open(project_path, 'w') as f:
                f.write(project_content)
                
            return True, f"Project file created at {project_path}", project_path
            
        except Exception as e:
            logger.error(f"Error generating project file: {str(e)}")
            return False, f"Error generating project file: {str(e)}", ""
    
    def _generate_project_content(self) -> str:
        """Generate the content for the KiCad project file."""
        # KiCad 9.0 project file is JSON format with updated version
        project = {
            "meta": {
                "version": 1
            },
            "version": 20230121,  # Updated version for KiCad 9.0
            "board": {
                "design_settings": {
                    "defaults": {
                        "board_outline_line_width": 0.1,
                        "copper_line_width": 0.2,
                        "copper_text_italic": False,
                        "copper_text_size_h": 1.5,
                        "copper_text_size_v": 1.5,
                        "copper_text_thickness": 0.3,
                        "copper_text_upright": False,
                        "courtyard_line_width": 0.05,
                        "dimension_precision": 4,
                        "dimension_units": 3,
                        "dimensions": {
                            "arrow_length": 1270000,
                            "extension_offset": 500000,
                            "keep_text_aligned": True,
                            "suppress_zeroes": False,
                            "text_position": 0,
                            "units_format": 1
                        },
                        "fab_line_width": 0.1,
                        "fab_text_italic": False,
                        "fab_text_size_h": 1.0,
                        "fab_text_size_v": 1.0,
                        "fab_text_thickness": 0.15,
                        "fab_text_upright": False,
                        "other_line_width": 0.15,
                        "other_text_italic": False,
                        "other_text_size_h": 1.0,
                        "other_text_size_v": 1.0,
                        "other_text_thickness": 0.15,
                        "other_text_upright": False,
                        "pads": {
                            "drill": 0.8,
                            "height": 1.6,
                            "width": 1.6
                        },
                        "silk_line_width": 0.15,
                        "silk_text_italic": False,
                        "silk_text_size_h": 1.0,
                        "silk_text_size_v": 1.0,
                        "silk_text_thickness": 0.15,
                        "silk_text_upright": False,
                        "zones": {
                            "min_clearance": 0.5
                        }
                    },
                    "diff_pair_dimensions": [],
                    "drc_exclusions": [],
                    "meta": {
                        "version": 2
                    },
                    "rule_severities": {
                        "annular_width": "error",
                        "clearance": "error",
                        "connection_width": "warning",
                        "copper_edge_clearance": "error",
                        "copper_sliver": "warning",
                        "courtyards_overlap": "error",
                        "diff_pair_gap_out_of_range": "error",
                        "diff_pair_uncoupled_length_too_long": "error",
                        "drill_out_of_range": "error",
                        "duplicate_footprints": "warning",
                        "extra_footprint": "warning",
                        "footprint": "error",
                        "footprint_type_mismatch": "error",
                        "hole_clearance": "error",
                        "hole_near_hole": "error",
                        "invalid_outline": "error",
                        "isolated_copper": "warning",
                        "item_on_disabled_layer": "error",
                        "items_not_allowed": "error",
                        "length_out_of_range": "error",
                        "lib_footprint_issues": "warning",
                        "lib_footprint_mismatch": "warning",
                        "malformed_courtyard": "error",
                        "microvia_drill_out_of_range": "error",
                        "missing_courtyard": "ignore",
                        "missing_footprint": "warning",
                        "net_conflict": "warning",
                        "npth_inside_courtyard": "ignore",
                        "padstack": "error",
                        "pth_inside_courtyard": "ignore",
                        "shorting_items": "error",
                        "silk_edge_clearance": "warning",
                        "silk_over_copper": "warning",
                        "silk_overlap": "warning",
                        "skew_out_of_range": "error",
                        "solder_mask_bridge": "error",
                        "starved_thermal": "error",
                        "text_height": "warning",
                        "text_thickness": "warning",
                        "through_hole_pad_without_hole": "error",
                        "too_many_vias": "error",
                        "track_dangling": "warning",
                        "track_width": "error",
                        "tracks_crossing": "error",
                        "unconnected_items": "error",
                        "unresolved_variable": "error",
                        "via_dangling": "warning",
                        "zones_intersect": "error"
                    },
                    "rules": {
                        "max_error": 0.005,
                        "min_clearance": 0.0,
                        "min_connection": 0.0,
                        "min_copper_edge_clearance": 0.0,
                        "min_hole_clearance": 0.25,
                        "min_hole_to_hole": 0.25,
                        "min_microvia_diameter": 0.2,
                        "min_microvia_drill": 0.1,
                        "min_resolved_spokes": 1,
                        "min_silk_clearance": 0.0,
                        "min_text_height": 0.8,
                        "min_text_thickness": 0.08,
                        "min_through_hole_diameter": 0.3,
                        "min_track_width": 0.2,
                        "min_via_annular_width": 0.05,
                        "min_via_diameter": 0.4,
                        "solder_mask_clearance": 0.0,
                        "solder_mask_min_width": 0.0,
                        "solder_mask_to_copper_clearance": 0.0,
                        "use_height_for_length_calcs": True
                    },
                    "track_widths": [
                        0.0,
                        0.2,
                        0.4,
                        0.6
                    ],
                    "via_dimensions": [
                        {
                            "diameter": 0.8,
                            "drill": 0.4
                        }
                    ],
                    "zones_allow_external_fillets": False
                },
                "layer_presets": [],
                "viewports": []
            },
            "net_settings": {
                "classes": [
                    {
                        "bus_width": 12.0,
                        "clearance": 0.2,
                        "diff_pair_gap": 0.25,
                        "diff_pair_via_gap": 0.25,
                        "diff_pair_width": 0.2,
                        "line_style": 0,
                        "microvia_diameter": 0.3,
                        "microvia_drill": 0.1,
                        "name": "Default",
                        "pcb_color": "rgba(0, 0, 0, 0.000)",
                        "schematic_color": "rgba(0, 0, 0, 0.000)",
                        "track_width": 0.25,
                        "via_diameter": 0.8,
                        "via_drill": 0.4
                    }
                ],
                "meta": {
                    "version": 3
                },
                "net_colors": None
            },
            "schematic": {
                "annotate_start_num": 0,
                "drawing": {
                    "dashed_lines_dash_length_ratio": 12.0,
                    "dashed_lines_gap_length_ratio": 3.0,
                    "default_line_thickness": 6.0,
                    "default_text_size": 50.0,
                    "field_names": [],
                    "intersheets_ref_own_page": False,
                    "intersheets_ref_prefix": "",
                    "intersheets_ref_short": False,
                    "intersheets_ref_show": False,
                    "intersheets_ref_suffix": "",
                    "junction_size_choice": 3,
                    "label_size_ratio": 0.375,
                    "pin_symbol_size": 25.0,
                    "text_offset_ratio": 0.15
                },
                "legacy_lib_dir": "",
                "legacy_lib_list": [],
                "meta": {
                    "version": 1
                },
                "pin_numbering_method": True,
                "net_format_name": "",
                "page_layout_descr_file": "",
                "plot_directory": "",
                "spice_adjust_passive_values": False,
                "spice_current_sheet_as_root": False,
                "spice_external_command": "spice \"%I\"",
                "spice_model_current_sheet_as_root": True,
                "spice_save_all_currents": False,
                "spice_save_all_voltages": False,
                "subpart_first_id": 65,
                "subpart_id_separator": 0
            },
            "sheets": [],
        }
        
        # Convert to JSON format with indentation
        return json.dumps(project, indent=2)
    
    def generate_netlist_file(self) -> Tuple[bool, str, str]:
        """
        Generate a KiCad netlist file (.net).
        
        Returns:
            Tuple of (success, message, file_path)
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Path for the netlist file
            netlist_path = os.path.join(self.output_dir, f"{self.project_name}.net")
            
            # Generate the netlist content
            netlist_content = self._generate_netlist_content()
            
            # Write to file
            with open(netlist_path, 'w') as f:
                f.write(netlist_content)
                
            return True, f"Netlist file created at {netlist_path}", netlist_path
            
        except Exception as e:
            logger.error(f"Error generating netlist file: {str(e)}")
            return False, f"Error generating netlist file: {str(e)}", ""
    
    def _generate_netlist_content(self) -> str:
        """Generate the content for the KiCad netlist file."""
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
        
        # Start with the header
        netlist = f"""(export (version D)
  (design
    (source "{self.project_name}")
    (date "{timestamp}")
    (tool "AI KiCad Project Generator")
  )
  (components
"""
        
        # Add components
        for comp in self.components:
            footprint = self.component_footprints.get(comp["type"], "")
            lib_id = self.component_libraries.get(comp["type"], "Device:Unknown")
            lib, part = lib_id.split(':')
            
            netlist += f"""    (comp (ref {comp["reference"]})
      (value {comp["value"]})
      (footprint {footprint})
      (libsource (lib {lib}) (part {part}))
      (tstamp {comp["uuid"]})
    )
"""
        
        # Add empty nets section if no connections
        if not self.connections:
            netlist += "  )\n  (nets\n    (net (code 0) (name \"GND\"))\n  )\n)"
            return netlist
            
        netlist += "  )\n  (nets\n"
        
        # Add GND net
        netlist += f"""    (net (code 0) (name "GND")
    )
"""
        
        # Add nets for connections
        for i, conn in enumerate(self.connections):
            netlist += f"""    (net (code {i+1}) (name "{conn["net_name"]}")
      (node (ref {conn["from"]}) (pin 1) (pintype passive))
      (node (ref {conn["to"]}) (pin 1) (pintype passive))
    )
"""
        
        # Close the netlist
        netlist += "  )\n)"
        
        return netlist
    
    def check_existing_project(self, project_path: str) -> bool:
        """
        Check if a project exists and load its contents for updating.
        
        Args:
            project_path: Path to the KiCad project file
            
        Returns:
            True if existing project was loaded
        """
        try:
            # Verify this is a valid KiCad project directory
            project_name = os.path.splitext(os.path.basename(project_path))[0]
            project_dir = os.path.dirname(project_path)
            
            # Check for essential project files
            schematic_path = os.path.join(project_dir, f"{project_name}.kicad_sch")
            pcb_path = os.path.join(project_dir, f"{project_name}.kicad_pcb")
            pro_path = os.path.join(project_dir, f"{project_name}.kicad_pro")
            
            if not os.path.exists(schematic_path) or not os.path.exists(pcb_path) or not os.path.exists(pro_path):
                logger.warning(f"Not a complete KiCad project at {project_path}")
                return False
                
            # Load the existing project files
            self.existing_files = {
                'schematic': self._load_file(schematic_path),
                'pcb': self._load_file(pcb_path),
                'project': self._load_file(pro_path),
            }
            
            # Set project attributes
            self.project_name = project_name
            self.output_dir = project_dir
            self.existing_project = True
            
            # Parse existing components from the schematic
            self._parse_existing_components()
            
            logger.info(f"Loaded existing project: {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading existing project: {str(e)}")
            return False
    
    def _load_file(self, file_path: str) -> str:
        """Load a file and return its contents."""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            return ""
    
    def _parse_existing_components(self) -> None:
        """Parse existing components from the schematic file."""
        try:
            # Reset current components and connections
            self.components = []
            self.connections = []
            
            if not self.existing_files.get('schematic'):
                return
                
            # Parse the schematic file based on format
            if '{' in self.existing_files['schematic'][:50]:
                # JSON-based format (KiCad 6+)
                self._parse_json_schematic()
            else:
                # S-expression format (older KiCad versions)
                self._parse_s_expr_schematic()
                
        except Exception as e:
            logger.error(f"Error parsing existing components: {str(e)}")
            
    def _parse_json_schematic(self) -> None:
        """Parse components from a JSON-based schematic file."""
        try:
            # Parse the JSON content
            schematic_data = json.loads(self.existing_files['schematic'])
            
            # Extract symbols (components)
            for symbol in schematic_data.get('symbols', []):
                ref = ""
                value = ""
                component_type = ""
                
                # Extract reference and value
                for prop in symbol.get('properties', []):
                    if prop.get('name') == 'Reference':
                        ref = prop.get('value', '')
                    elif prop.get('name') == 'Value':
                        value = prop.get('value', '')
                
                # Determine component type from lib_id
                lib_id = symbol.get('lib_id', '')
                for comp_type, lib_ref in self.component_libraries.items():
                    if lib_ref == lib_id:
                        component_type = comp_type
                        break
                
                # If we couldn't determine the type from lib_id, try from reference
                if not component_type and ref:
                    prefix = ref[0] if ref else ""
                    component_type = self._get_component_type_from_prefix(prefix)
                
                # Add to our components list
                self.components.append({
                    'type': component_type or 'unknown',
                    'value': value,
                    'reference': ref,
                    'uuid': symbol.get('uuid', self._generate_uuid()),
                    'position': symbol.get('at', {'x': 100, 'y': 100}),
                })
                
                # Add to UUID map
                if ref:
                    self.uuid_map[ref] = symbol.get('uuid', '')
                    
        except Exception as e:
            logger.error(f"Error parsing JSON schematic: {str(e)}")
    
    def _parse_s_expr_schematic(self) -> None:
        """Parse components from an S-expression based schematic file."""
        try:
            # Simple regex-based parsing for S-expressions
            comp_pattern = r'\(comp\s+\(ref\s+([^\)]+)\)[^)]*\(value\s+([^\)]+)\)'
            matches = re.finditer(comp_pattern, self.existing_files['schematic'])
            
            for match in matches:
                ref = match.group(1)
                value = match.group(2)
                
                # Determine component type from reference
                prefix = ref[0] if ref else ""
                component_type = self._get_component_type_from_prefix(prefix)
                
                # Add to our components list
                self.components.append({
                    'type': component_type or 'unknown',
                    'value': value,
                    'reference': ref,
                    'uuid': self._generate_uuid(),
                    'position': {'x': 100, 'y': 100},
                })
                
                # Add to UUID map
                self.uuid_map[ref] = self.components[-1]['uuid']
                
        except Exception as e:
            logger.error(f"Error parsing S-expression schematic: {str(e)}")
    
    def _get_component_type_from_prefix(self, prefix: str) -> str:
        """Get component type from reference prefix."""
        prefix_map = {
            'R': 'resistor',
            'C': 'capacitor',
            'L': 'inductor',
            'D': 'diode',
            'Q': 'transistor',
            'SW': 'switch',
            'J': 'connector',
            'U': 'ic',
            'A': 'arduino',
            'Y': 'crystal',
            'F': 'fuse',
            'X': 'oscillator',
            'RV': 'voltage_regulator',
            'OP': 'opamp',
            'K': 'relay',
        }
        return prefix_map.get(prefix, 'unknown')
    
    def update_project_from_description(self, description: str) -> Tuple[bool, str, Dict[str, str]]:
        """
        Update an existing project based on a new description.
        
        Args:
            description: Natural language description of the changes
            
        Returns:
            Tuple of (success, message, dict of updated files)
        """
        try:
            if not self.existing_project:
                return False, "No existing project loaded", {}
                
            # Extract changes from the description
            new_components, removed_refs, modified_components, new_connections = self._parse_change_description(description)
            
            # Add new components
            for comp in new_components:
                self.components.append(comp)
                self.uuid_map[comp['reference']] = comp['uuid']
                
            # Remove components
            self.components = [c for c in self.components if c['reference'] not in removed_refs]
            
            # Update modified components
            for mod_comp in modified_components:
                for comp in self.components:
                    if comp['reference'] == mod_comp['reference']:
                        comp.update(mod_comp)
                        break
                        
            # Add new connections
            for conn in new_connections:
                self.connections.append(conn)
                
            # Generate updated project files
            results = {}
            
            # Generate schematic
            sch_success, sch_message, sch_path = self.generate_schematic_file()
            results["schematic"] = sch_path
            
            # Generate PCB
            pcb_success, pcb_message, pcb_path = self.generate_pcb_file()
            results["pcb"] = pcb_path
            
            # Generate project file
            pro_success, pro_message, pro_path = self.generate_project_file()
            results["project"] = pro_path
            
            # Generate netlist
            net_success, net_message, net_path = self.generate_netlist_file()
            results["netlist"] = net_path
            
            all_success = sch_success and pcb_success and pro_success and net_success
            
            if all_success:
                return True, f"Successfully updated KiCad project in {self.output_dir}", results
            else:
                return False, f"Partial success: {sch_message}; {pcb_message}; {pro_message}; {net_message}", results
                
        except Exception as e:
            logger.error(f"Error updating project: {str(e)}")
            return False, f"Error updating project: {str(e)}", {}
    
    def _parse_change_description(self, description: str) -> Tuple[List[Dict], List[str], List[Dict], List[Dict]]:
        """
        Parse a description of changes to make to the project.
        
        Args:
            description: Natural language description of changes
            
        Returns:
            Tuple of (new_components, removed_refs, modified_components, new_connections)
        """
        new_components = []
        removed_refs = []
        modified_components = []
        new_connections = []
        
        try:
            # Extract component additions with regex patterns
            add_patterns = {
                'resistor': r'add(?:\s+a)?\s+(?:new\s+)?(\d+(?:\.\d+)?)\s*(?:k|K|M|G|m)?\s*(?:ohm|Ω|OHM)?\s+resistor',
                'capacitor': r'add(?:\s+a)?\s+(?:new\s+)?(\d+(?:\.\d+)?)\s*(?:n|u|µ|p|m|f)?\s*(?:F|farad)?\s+capacitor',
                'led': r'add(?:\s+a)?\s+(?:new\s+)?(red|green|blue|yellow|white)?\s*LED',
                'transistor': r'add(?:\s+a)?\s+(?:new\s+)?(NPN|PNP|MOSFET)?\s*transistor',
                'switch': r'add(?:\s+a)?\s+(?:new\s+)?(?:push\s+)?switch|button',
                'connector': r'add(?:\s+a)?\s+(?:new\s+)?(\d+)?\s*(?:pin\s+)?connector',
            }
            
            # Extract component additions
            for comp_type, pattern in add_patterns.items():
                matches = re.finditer(pattern, description, re.IGNORECASE)
                
                for match in matches:
                    value = ""
                    if len(match.groups()) > 0 and match.group(1):
                        value = match.group(1)
                    
                    # Add to new components
                    ref_prefix = self._get_ref_prefix(comp_type)
                    next_num = self._get_next_ref_number(ref_prefix)
                    reference = f"{ref_prefix}{next_num}"
                    
                    new_components.append({
                        'type': comp_type,
                        'value': self._parse_component_value(comp_type, value),
                        'reference': reference,
                        'uuid': self._generate_uuid(),
                        'position': {'x': 100 + len(new_components) * 30, 'y': 100},
                    })
            
            # Extract components to remove
            remove_pattern = r'remove\s+(?:component\s+)?([A-Z][A-Z0-9]*)'
            remove_matches = re.finditer(remove_pattern, description, re.IGNORECASE)
            
            for match in remove_matches:
                ref = match.group(1).upper()
                removed_refs.append(ref)
            
            # Extract components to modify
            modify_pattern = r'change\s+(?:the\s+)?(?:value\s+of\s+)?([A-Z][A-Z0-9]*)\s+to\s+([a-zA-Z0-9\.\s]+)'
            modify_matches = re.finditer(modify_pattern, description, re.IGNORECASE)
            
            for match in modify_matches:
                ref = match.group(1).upper()
                new_value = match.group(2).strip()
                
                # Find component type
                comp_type = 'unknown'
                for comp in self.components:
                    if comp['reference'] == ref:
                        comp_type = comp['type']
                        break
                
                modified_components.append({
                    'reference': ref,
                    'value': self._parse_component_value(comp_type, new_value),
                })
            
            # Extract new connections
            connect_pattern = r'connect\s+([A-Z][A-Z0-9]*)\s+(?:to|and)\s+([A-Z][A-Z0-9]*)'
            connect_matches = re.finditer(connect_pattern, description, re.IGNORECASE)
            
            for match in connect_matches:
                from_ref = match.group(1).upper()
                to_ref = match.group(2).upper()
                
                # Check if components exist
                from_exists = any(comp['reference'] == from_ref for comp in self.components + new_components)
                to_exists = any(comp['reference'] == to_ref for comp in self.components + new_components)
                
                if from_exists and to_exists:
                    new_connections.append({
                        'from': from_ref,
                        'to': to_ref,
                        'net_name': f"Net-{from_ref}-{to_ref}",
                        'uuid': self._generate_uuid(),
                    })
            
            return new_components, removed_refs, modified_components, new_connections
            
        except Exception as e:
            logger.error(f"Error parsing change description: {str(e)}")
            return [], [], [], []
            
    def _get_next_ref_number(self, prefix: str) -> int:
        """Get the next available reference number for a given prefix."""
        existing_numbers = []
        
        for comp in self.components:
            ref = comp['reference']
            if ref.startswith(prefix):
                try:
                    number = int(ref[len(prefix):])
                    existing_numbers.append(number)
                except ValueError:
                    continue
        
        if not existing_numbers:
            return 1
        
        return max(existing_numbers) + 1
    
    def generate_complete_project(self, description: str, project_name: str = None) -> Tuple[bool, str, Dict[str, str]]:
        """
        Generate a complete KiCad project from a natural language description.
        
        Args:
            description: Natural language description of the circuit
            project_name: Optional project name (defaults to cleaned version of description)
            
        Returns:
            Tuple of (success, message, dict of generated files)
        """
        try:
            # Set project name if provided
            if project_name:
                self.set_project_name(project_name)
            else:
                # Use first 30 chars of description as project name
                self.set_project_name(description[:30])
            
            # Process the description
            success, message = self.process_description(description)
            if not success:
                return False, message, {}
            
            # Generate all project files
            results = {}
            
            # Generate schematic
            logger.info("Generating schematic file...")
            schematic_content = self._generate_schematic_content()
            logger.info(f"Schematic content starts with: {schematic_content[:100]}")
            sch_success, sch_message, sch_path = self.generate_schematic_file()
            results["schematic"] = sch_path
            
            # Generate PCB
            logger.info("Generating PCB file...")
            pcb_content = self._generate_pcb_content()
            logger.info(f"PCB content starts with: {pcb_content[:100]}")
            pcb_success, pcb_message, pcb_path = self.generate_pcb_file()
            results["pcb"] = pcb_path
            
            # Generate project file
            logger.info("Generating project file...")
            project_content = self._generate_project_content()
            logger.info(f"Project content starts with: {project_content[:100]}")
            pro_success, pro_message, pro_path = self.generate_project_file()
            results["project"] = pro_path
            
            # Generate netlist
            logger.info("Generating netlist file...")
            netlist_content = self._generate_netlist_content()
            logger.info(f"Netlist content starts with: {netlist_content[:100]}")
            net_success, net_message, net_path = self.generate_netlist_file()
            results["netlist"] = net_path
            
            all_success = sch_success and pcb_success and pro_success and net_success
            
            if all_success:
                return True, f"Successfully generated KiCad project with {len(self.components)} components in {self.output_dir}", results
            else:
                return False, f"Partial success: {sch_message}; {pcb_message}; {pro_message}; {net_message}", results
                
        except Exception as e:
            logger.error(f"Error generating complete project: {str(e)}")
            return False, f"Error generating complete project: {str(e)}", {}
    
    def open_kicad_editor(self, file_path: str) -> Tuple[bool, str]:
        """
        Open a KiCad project file in the appropriate editor.
        
        Args:
            file_path: Path to the KiCad file (.kicad_sch or .kicad_pcb)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File {file_path} does not exist"
                
            # Get file extension to determine which editor to launch
            _, ext = os.path.splitext(file_path)
            
            # Path to KiCad executable on Mac (common location)
            kicad_path = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad"
            
            # Check if we're on macOS
            if sys.platform == 'darwin':
                # Use the 'open' command on macOS which is more reliable
                subprocess.Popen(['open', file_path])
                file_type = ""
                if ext == '.kicad_sch':
                    file_type = "Schematic"
                elif ext == '.kicad_pcb':
                    file_type = "PCB"
                elif ext == '.kicad_pro':
                    file_type = "Project"
                return True, f"Opened KiCad {file_type} file with default application: {file_path}"
            
            # Check if KiCad exists at the expected path
            if not os.path.exists(kicad_path):
                return False, f"KiCad not found at {kicad_path}. Please ensure KiCad is installed correctly."
            
            # Determine the appropriate KiCad application based on the file extension
            if ext == '.kicad_sch':
                # Launch KiCad Schematic Editor
                subprocess.Popen([kicad_path, file_path])
                return True, f"Launched Schematic Editor with {file_path}"
            elif ext == '.kicad_pcb':
                # Launch KiCad PCB Editor
                subprocess.Popen([kicad_path, file_path])
                return True, f"Launched PCB Editor with {file_path}"
            elif ext == '.kicad_pro':
                # Launch KiCad Project Manager
                subprocess.Popen([kicad_path, file_path])
                return True, f"Launched KiCad Project Manager with {file_path}"
            else:
                return False, f"Unsupported file type: {ext}"
                
        except Exception as e:
            logger.error(f"Error opening KiCad editor: {str(e)}")
            return False, f"Error opening KiCad editor: {str(e)}"
    
    def open_schematic_editor(self) -> Tuple[bool, str]:
        """
        Open the current project's schematic file in KiCad Schematic Editor.
        
        Returns:
            Tuple of (success, message)
        """
        schematic_path = os.path.join(self.output_dir, f"{self.project_name}.kicad_sch")
        
        if not os.path.exists(schematic_path):
            return False, f"Schematic file not found at {schematic_path}. Generate the schematic first."
            
        return self.open_kicad_editor(schematic_path)
    
    def open_pcb_editor(self) -> Tuple[bool, str]:
        """
        Open the current project's PCB file in KiCad PCB Editor.
        
        Returns:
            Tuple of (success, message)
        """
        pcb_path = os.path.join(self.output_dir, f"{self.project_name}.kicad_pcb")
        
        if not os.path.exists(pcb_path):
            return False, f"PCB file not found at {pcb_path}. Generate the PCB first."
            
        return self.open_kicad_editor(pcb_path)
    
    def open_project(self) -> Tuple[bool, str]:
        """
        Open the current project in KiCad Project Manager.
        
        Returns:
            Tuple of (success, message)
        """
        project_path = os.path.join(self.output_dir, f"{self.project_name}.kicad_pro")
        
        if not os.path.exists(project_path):
            return False, f"Project file not found at {project_path}. Generate the project first."
            
        return self.open_kicad_editor(project_path)