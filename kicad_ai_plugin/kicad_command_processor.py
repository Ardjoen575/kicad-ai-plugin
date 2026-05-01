import os
import logging
import json
import re
import tempfile
from typing import Dict, List, Optional, Tuple

# Import the project generator
from .kicad_project_generator import KiCadProjectGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import skip  # type: ignore
    SKIP_AVAILABLE = True
    logger.info("kicad-skip library loaded successfully")
except ImportError:
    SKIP_AVAILABLE = False
    logger.warning("kicad-skip library not available. Install with: pip install kicad-skip")

try:
    import skidl  # type: ignore
    from skidl import Part, Net, generate_netlist, KICAD  # type: ignore
    SKIDL_AVAILABLE = True
    logger.info("SKiDL library loaded successfully")
except ImportError:
    SKIDL_AVAILABLE = False
    logger.warning("SKiDL library not available. Install with: pip install skidl")

class KiCadDesignAgent:
    """Agent that uses SKiDL to create KiCad designs from natural language commands"""
    
    def __init__(self):
        self.current_design = {}
        self.components = {}
        self.nets = {}
        self.library_mapping = {
            'resistor': ('Device', 'R'),
            'capacitor': ('Device', 'C'),
            'inductor': ('Device', 'L'),
            'diode': ('Device', 'D'),
            'led': ('Device', 'LED'),
            'transistor': ('Device', 'Q_NPN_CBE'),
            'switch': ('Switch', 'SW_Push'),
            'connector': ('Connector', 'Conn_01x02_Male'),
            'ic': ('Device', 'IC'),
        }
    
    def create_part(self, part_type, value=None, reference=None):
        """Create a new part using SKiDL"""
        if not SKIDL_AVAILABLE:
            return False, "SKiDL library not available"
            
        try:
            # Map part type to KiCad library and part
            part_type_lower = part_type.lower()
            lib_and_part = None
            
            for key, mapping in self.library_mapping.items():
                if key in part_type_lower:
                    lib_and_part = mapping
                    break
                    
            if not lib_and_part:
                return False, f"Unknown part type: {part_type}"
                
            # Create the part
            lib_name, part_name = lib_and_part
            new_part = Part(lib_name, part_name)
            
            # Set value if provided
            if value:
                new_part.value = value
                
            # Set reference if provided
            if reference:
                new_part.ref = reference
                
            # Store the part
            ref = new_part.ref
            self.components[ref] = new_part
            
            return True, f"Created {part_type} with reference {ref} and value {value}"
            
        except Exception as e:
            logger.error(f"Error creating part: {str(e)}")
            return False, f"Error creating part: {str(e)}"
    
    def connect_parts(self, from_ref, to_ref, from_pin=None, to_pin=None):
        """Connect two parts together"""
        if not SKIDL_AVAILABLE:
            return False, "SKiDL library not available"
            
        try:
            # Check if parts exist
            if from_ref not in self.components:
                return False, f"Component {from_ref} not found"
                
            if to_ref not in self.components:
                return False, f"Component {to_ref} not found"
                
            from_part = self.components[from_ref]
            to_part = self.components[to_ref]
            
            # Create a new net
            net_name = f"Net_{from_ref}_{to_ref}"
            new_net = Net(net_name)
            
            # Connect the parts
            if from_pin and to_pin:
                from_part[from_pin] += new_net
                to_part[to_pin] += new_net
            else:
                # Connect first pins by default
                from_part[1] += new_net
                to_part[1] += new_net
                
            # Store the net
            self.nets[net_name] = new_net
            
            return True, f"Connected {from_ref} to {to_ref}"
            
        except Exception as e:
            logger.error(f"Error connecting parts: {str(e)}")
            return False, f"Error connecting parts: {str(e)}"
            
    def generate_circuit(self, output_dir=None):
        """Generate a KiCad netlist from the circuit design"""
        if not SKIDL_AVAILABLE:
            return False, "SKiDL library not available"
            
        try:
            # Generate the netlist
            if not output_dir:
                output_dir = tempfile.gettempdir()
                
            netlist_file = os.path.join(output_dir, "skidl_circuit.net")
            
            # Generate the netlist
            generate_netlist(netlist_file)
            
            return True, f"Generated netlist: {netlist_file}"
            
        except Exception as e:
            logger.error(f"Error generating circuit: {str(e)}")
            return False, f"Error generating circuit: {str(e)}"
            
class KiCadCommandProcessor:
    """Processes natural language commands for KiCad and generates project files"""
    
    def __init__(self):
        self.component_counter = {
            'R': 1,  # Resistors
            'C': 1,  # Capacitors
            'L': 1,  # Inductors
            'D': 1,  # Diodes
            'Q': 1,  # Transistors
            'U': 1,  # ICs
            'J': 1,  # Connectors
            'SW': 1,  # Switches
            'LED': 1,  # LEDs
            'X': 1,  # Crystals/Oscillators
            'Y': 1,  # Crystals
            'F': 1,  # Fuses
            'T': 1,  # Transformers
            'VR': 1,  # Variable Resistors
            'TP': 1,  # Test Points
        }
        self.current_schematic = None
        self.current_pcb = None
        self.output_dir = os.path.join(os.path.expanduser("~"), "Documents", "KiCadProjects", "AIGenerated")
        self.project_generator = KiCadProjectGenerator(output_dir=self.output_dir)
        self.current_project_path = None
        
    def process_command(self, command_text: str) -> Tuple[str, str, bool]:
        """
        Process a natural language command for KiCad.
        
        Args:
            command_text: The command text
            
        Returns:
            Tuple of (response message, execution log, success flag)
        """
        try:
            # Remove the "@kicad" prefix if present
            if command_text.lower().startswith("@kicad"):
                command_text = command_text[6:].strip()
                
            # Initialize project generator
            output_dir = os.path.expanduser("~/Documents/KiCadProjects/AIGenerated")
            os.makedirs(output_dir, exist_ok=True)
            project_generator = KiCadProjectGenerator(output_dir=output_dir)
            
            # Check if this is a command to rename an existing project
            if "rename" in command_text.lower():
                # Try to extract the new name
                name_match = re.search(r'(?:rename|name)\s+(?:to|as|the|project|project\s+name\s+to)\s*["\']?([^"\']+)["\']?', command_text)
                
                if not name_match:
                    return "I couldn't understand the new name for the project. Please use format: '@kicad rename project to \"new_name\"'", "Could not extract new name", False
                
                new_name = name_match.group(1).strip()
                
                # Find any existing project
                pro_files = [f for f in os.listdir(output_dir) if f.endswith(".kicad_pro")]
                if not pro_files:
                    return "No existing projects found to rename.", "No projects found", False
                
                # Load the most recent project
                project_path = os.path.join(output_dir, pro_files[0])
                if not project_generator.check_existing_project(project_path):
                    return f"Could not load project at {project_path}", "Failed to load project", False
                
                # Rename the project
                success, message, files = project_generator.rename_project(new_name)
                
                if success:
                    response = f"I've renamed the KiCad project to '{project_generator.project_name}':\n\n"
                    response += f"Command: {command_text}\n\n"
                    response += f"Original project: {os.path.basename(project_path)}\n"
                    response += f"New project name: {project_generator.project_name}\n"
                    response += f"Project location: {output_dir}\n\n"
                    response += f"Files renamed:\n"
                    for file_type, path in files.items():
                        response += f"- {file_type.capitalize()}: {os.path.basename(path)}\n"
                    
                    response += f"\nStatus: Success ✅\n\n"
                    response += f"To open the renamed project in KiCad:\n"
                    response += f"1. Launch KiCad\n"
                    response += f"2. Use File > Open Project\n"
                    response += f"3. Navigate to: {output_dir}\n"
                    response += f"4. Select the {project_generator.project_name}.kicad_pro file\n"
                    
                    return response, message, True
                else:
                    return f"Error renaming project: {message}", message, False
            
            # Check if this is a command to create a new project
            elif "create" in command_text.lower() and "project" in command_text.lower():
                # Extract project name if specified
                name_match = re.search(r'(?:named|called|name)\s+["\']?([^"\']+)["\']?', command_text)
                project_name = name_match.group(1).strip() if name_match else None
                
                # Generate a complete project from the description
                success, message, files = project_generator.generate_complete_project(command_text, project_name)
                
                if success:
                    # Build response
                    response = f"I've generated a complete KiCad project based on your description:\n\n"
                    response += f"Command: {command_text}\n\n"
                    response += f"Project name: {project_generator.project_name}\n"
                    response += f"Project location: {output_dir}\n\n"
                    response += f"Files created:\n"
                    response += f"- Schematic: {os.path.basename(files.get('schematic', ''))}\n"
                    response += f"- PCB: {os.path.basename(files.get('pcb', ''))}\n"
                    response += f"- Project: {os.path.basename(files.get('project', ''))}\n"
                    response += f"- Netlist: {os.path.basename(files.get('netlist', ''))}\n\n"
                    
                    response += f"Status: Success ✅\n\n"
                    response += f"To open the project in KiCad:\n"
                    response += f"1. Launch KiCad\n"
                    response += f"2. Use File > Open Project\n"
                    response += f"3. Navigate to: {output_dir}\n"
                    response += f"4. Select the .kicad_pro file\n\n"
                    
                    response += f"You can now make further changes to the project by saying \"@kicad update the project to add a 10k resistor\" etc."
                    
                    return response, message, True
                else:
                    return f"Error generating project: {message}", message, False
            
            # Check if this is a command to update an existing project
            elif "update" in command_text.lower() or "modify" in command_text.lower() or "change" in command_text.lower() or "fix" in command_text.lower():
                # Find existing projects in the output directory
                pro_files = [f for f in os.listdir(output_dir) if f.endswith(".kicad_pro")]
                if not pro_files:
                    return "No existing projects found to update.", "No projects found", False
                    
                # Use the most recent project
                project_path = os.path.join(output_dir, pro_files[0])
                
                # Load the existing project
                if not project_generator.check_existing_project(project_path):
                    return f"Error: Could not load existing project at {project_path}.", "Project load failed.", False
                
                # Update the project based on the description
                success, message, files = project_generator.update_project_from_description(command_text)
                
                if success:
                    # Build response
                    response = f"I've updated the KiCad project based on your description:\n\n"
                    response += f"Command: {command_text}\n\n"
                    response += f"Project path: {project_path}\n"
                    response += f"Project location: {output_dir}\n\n"
                    response += f"Files updated:\n"
                    response += f"- Schematic: {os.path.basename(files.get('schematic', ''))}\n"
                    response += f"- PCB: {os.path.basename(files.get('pcb', ''))}\n"
                    response += f"- Project: {os.path.basename(files.get('project', ''))}\n"
                    response += f"- Netlist: {os.path.basename(files.get('netlist', ''))}\n\n"
                    
                    response += f"Status: Success ✅\n\n"
                    response += f"Open the project in KiCad to see the updated design. If you have the project already open, use \"File > Reload\" to see the changes."
                    
                    return response, message, True
                else:
                    return f"Error updating project: {message}", message, False
            
            # Command not recognized
            else:
                # Try to process the command as a general circuit description
                success, message, files = project_generator.generate_complete_project(command_text)
                
                if success:
                    # Build response for general circuit generation
                    response = f"I've created a new KiCad project based on your description:\n\n"
                    response += f"Command: {command_text}\n\n"
                    response += f"Project name: {project_generator.project_name}\n"
                    response += f"Project location: {output_dir}\n\n"
                    response += f"Files created:\n"
                    response += f"- Schematic: {os.path.basename(files.get('schematic', ''))}\n"
                    response += f"- PCB: {os.path.basename(files.get('pcb', ''))}\n"
                    response += f"- Project: {os.path.basename(files.get('project', ''))}\n"
                    response += f"- Netlist: {os.path.basename(files.get('netlist', ''))}\n\n"
                    
                    response += f"Status: Success ✅\n\n"
                    response += f"To open the project in KiCad:\n"
                    response += f"1. Launch KiCad\n"
                    response += f"2. Use File > Open Project\n"
                    response += f"3. Navigate to: {output_dir}\n"
                    response += f"4. Select the .kicad_pro file\n\n"
                    
                    return response, message, True
                else:
                    return f"I couldn't understand how to process your KiCad command. Try:\n- @kicad Create a new project with...\n- @kicad Update the project to add...", "Command not recognized", False
        
        except Exception as e:
            logger.error(f"Error processing KiCad command: {str(e)}")
            return f"Error processing command: {str(e)}", str(e), False
            
    def _is_update_project_command(self, command: str) -> bool:
        """Check if the command is about updating an existing project"""
        update_keywords = ["update", "modify", "change", "edit"]
        project_words = ["project", "schematic", "design", "circuit", "pcb"]
        
        has_update_keyword = any(word in command.lower() for word in update_keywords)
        has_project_word = any(word in command.lower() for word in project_words)
        
        # Check for specific update patterns
        update_patterns = [
            r'add\s+(?:a\s+)?new\s+component',
            r'add\s+(?:a\s+)?(\d+)?\s*(?:ohm|Ω)?\s*resistor',
            r'add\s+(?:a\s+)?(\d+)?\s*(?:farad|F)?\s*capacitor',
            r'add\s+(?:a\s+)?LED',
            r'remove\s+component',
            r'connect\s+([A-Z][A-Z0-9]*)\s+to\s+([A-Z][A-Z0-9]*)',
            r'change\s+(?:the\s+)?value\s+of\s+([A-Z][A-Z0-9]*)',
        ]
        
        has_specific_pattern = any(re.search(pattern, command, re.IGNORECASE) for pattern in update_patterns)
        
        return (has_update_keyword and has_project_word) or has_specific_pattern
    
    def _handle_project_update(self, command: str) -> Tuple[str, str, bool]:
        """Handle commands to update an existing KiCad project"""
        try:
            # Check if we have an active project
            if not self.current_project_path:
                # Try to find a KiCad project in the current directory
                project_files = self._find_kicad_projects_in_dir(self.output_dir)
                
                if not project_files:
                    return (
                        "No active KiCad project to update. Please specify a project path or create a new project first.",
                        "No active project found",
                        False
                    )
                
                # Use the most recently modified project file
                self.current_project_path = project_files[0]
            
            # Load the existing project
            if not self.project_generator.check_existing_project(self.current_project_path):
                return (
                    f"Failed to load the project at {self.current_project_path}. Please check if it's a valid KiCad project.",
                    f"Failed to load project: {self.current_project_path}",
                    False
                )
            
            # Update the project with the new description
            success, message, files = self.project_generator.update_project_from_description(command)
            
            if success:
                response = f"""I've updated the KiCad project based on your description:

Command: {command}

Project path: {self.current_project_path}
Project location: {self.output_dir}

Files updated:
- Schematic: {os.path.basename(files.get('schematic', 'N/A'))}
- PCB: {os.path.basename(files.get('pcb', 'N/A'))}
- Project: {os.path.basename(files.get('project', 'N/A'))}
- Netlist: {os.path.basename(files.get('netlist', 'N/A'))}

Status: Success ✅

Open the project in KiCad to see the updated design. If you have the project already open, use "File > Reload" to see the changes.
"""
            else:
                response = f"""I encountered some issues while updating the KiCad project:

Command: {command}

Project path: {self.current_project_path}

Status: Partial success or Failure ❌

Error details: {message}

Please check the project files and try again with a more specific command.
"""
            
            return response, message, success
            
        except Exception as e:
            logger.error(f"Error updating project: {str(e)}")
            return f"Error updating project: {str(e)}", str(e), False
    
    def _find_kicad_projects_in_dir(self, directory: str) -> List[str]:
        """Find KiCad project files in a directory, sorted by modification time (newest first)"""
        try:
            project_files = []
            
            # Look for .kicad_pro files
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.kicad_pro'):
                        project_path = os.path.join(root, file)
                        project_files.append(project_path)
            
            # Sort by modification time, newest first
            project_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            return project_files
        except Exception as e:
            logger.error(f"Error finding KiCad projects: {str(e)}")
            return []
            
    def _handle_project_generation(self, command: str) -> Tuple[str, str, bool]:
        """Handle commands to generate a complete KiCad project"""
        try:
            # Extract project name if specified
            project_name_match = re.search(r'(?:named|called)\s+[\"\']?([a-zA-Z0-9_\- ]+)[\"\']?', command)
            project_name = project_name_match.group(1) if project_name_match else "ai_generated_project"
            
            # Generate the project
            success, message, files = self.project_generator.generate_complete_project(command, project_name)
            
            if success:
                # Store the current project path
                self.current_project_path = files.get('project', '')
                
                response = f"""I've generated a complete KiCad project based on your description:

Command: {command}

Project name: {project_name}
Project location: {self.output_dir}

Files created:
- Schematic: {os.path.basename(files.get('schematic', 'N/A'))}
- PCB: {os.path.basename(files.get('pcb', 'N/A'))}
- Project: {os.path.basename(files.get('project', 'N/A'))}
- Netlist: {os.path.basename(files.get('netlist', 'N/A'))}

Status: Success ✅

To open the project in KiCad:
1. Launch KiCad
2. Use File > Open Project
3. Navigate to: {self.output_dir}
4. Select the .kicad_pro file

You can now make further changes to the project by saying "@kicad update the project to add a 10k resistor" etc.
"""
            else:
                response = f"""I encountered some issues while generating the KiCad project:

Command: {command}

Project name: {project_name}

Status: Partial success or Failure ❌

Error details: {message}

Please try again with a more detailed component description.
"""
            
            return response, message, success
            
        except Exception as e:
            logger.error(f"Error generating project: {str(e)}")
            return f"Error generating project: {str(e)}", str(e), False

    def set_current_project(self, project_path: str) -> Tuple[bool, str]:
        """
        Set the current project to work with.
        
        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if not os.path.exists(project_path):
                return False, f"Project file does not exist: {project_path}"
                
            if not project_path.endswith('.kicad_pro'):
                return False, "The file must be a KiCad project file (.kicad_pro)"
                
            # Load the project into the generator
            if not self.project_generator.check_existing_project(project_path):
                return False, "Failed to load the project. Please check if it's a valid KiCad project."
                
            # Set as current project
            self.current_project_path = project_path
            
            # Update output directory to match project location
            self.output_dir = os.path.dirname(project_path)
            self.project_generator.output_dir = self.output_dir
            
            return True, f"Successfully set current project to: {project_path}"
            
        except Exception as e:
            logger.error(f"Error setting current project: {str(e)}")
            return False, f"Error setting current project: {str(e)}"

    def _is_generate_project_command(self, command: str) -> bool:
        """Check if the command is about generating a complete project"""
        keywords = ["generate", "create", "make", "build"]
        project_words = ["project", "schematic", "design", "circuit", "pcb"]
        
        has_keyword = any(word in command.lower() for word in keywords)
        has_project_word = any(word in command.lower() for word in project_words)
        
        return has_keyword and has_project_word
            
    def _generate_component_script(self, command: str) -> Tuple[bool, List[str], str]:
        """Generate a SKiDL script to create components based on the command"""
        log = []
        success = False
        
        try:
            # Extract component information
            components = self._extract_components(command)
            log.append(f"Found components to add: {components}")
            
            if not components:
                log.append(f"No components could be extracted from command: {command}")
                return False, log, ""
            
            # Generate SKiDL script
            script_lines = [
                "# Generated SKiDL script for KiCad",
                "from skidl import *",
                "",
                "# Initialize the circuit",
                "lib_search_paths_kicad = ['/usr/share/kicad/library']  # Update this path for your system",
                "",
                "# Create parts"
            ]
            
            # Add each component to the script
            for comp_type, comp_info in components:
                try:
                    # Get next reference number
                    ref = self._get_next_reference(comp_type)
                    
                    # Get value (default to something reasonable if not specified)
                    value = comp_info.get('value', '')
                    if not value and comp_type == 'R':
                        value = '10k'
                    elif not value and comp_type == 'C':
                        value = '10uF'
                    
                    # Map component type to SKiDL
                    lib_part = self._map_component_to_lib(comp_type)
                    
                    # Add component creation to script
                    script_lines.append(f"{ref} = Part('{lib_part[0]}', '{lib_part[1]}', ref='{ref}', value='{value}')")
                    
                    log.append(f"Added {comp_type} component with reference {ref}, value {value} to script")
                    
                    # Increment the counter
                    self.component_counter[comp_type] += 1
                    
                except Exception as e:
                    log.append(f"Error adding component {comp_type} to script: {str(e)}")
                    return False, log, ""
            
            # Add netlist generation
            script_lines.extend([
                "",
                "# Generate netlist",
                "generate_netlist()",
                "",
                "# To use this script:",
                "# 1. Save this to a .py file",
                "# 2. Install SKiDL: pip install skidl",
                "# 3. Run: python this_script.py",
                "# 4. Import the generated netlist in KiCad"
            ])
            
            # Join script lines
            final_script = "\n".join(script_lines)
            
            # Assuming we got here, we succeeded
            success = True
            log.append("Script generated successfully")
            
            return success, log, final_script
            
        except Exception as e:
            log.append(f"Error in generating component script: {str(e)}")
            success = False
            return success, log, ""
            
    def _generate_connection_script(self, command: str) -> Tuple[bool, List[str], str]:
        """Generate a SKiDL script to connect components based on the command"""
        log = []
        success = False
        
        try:
            # Extract connection information
            connections = self._extract_connections(command)
            log.append(f"Found connections to make: {connections}")
            
            if not connections:
                log.append(f"No connections could be extracted from command: {command}")
                return False, log, ""
            
            # Generate SKiDL script
            script_lines = [
                "# Generated SKiDL script for KiCad",
                "from skidl import *",
                "",
                "# Initialize the circuit",
                "lib_search_paths_kicad = ['/usr/share/kicad/library']  # Update this path for your system",
                "",
                "# Create parts (you may need to modify these based on your specific components)",
            ]
            
            # Add components from connections
            components = set()
            for conn in connections:
                components.add(conn['from'])
                components.add(conn['to'])
                
            for comp in components:
                # Try to extract component type from reference
                comp_type = ''.join(c for c in comp if not c.isdigit())
                lib_part = self._map_component_to_lib(comp_type)
                script_lines.append(f"{comp} = Part('{lib_part[0]}', '{lib_part[1]}', ref='{comp}')")
            
            script_lines.append("")
            script_lines.append("# Create nets for connections")
            
            # Add each connection
            for i, conn in enumerate(connections):
                try:
                    # Create net and connect components
                    net_name = f"net_{i}"
                    script_lines.append(f"{net_name} = Net('{conn['from']}_{conn['to']}')")
                    script_lines.append(f"{conn['from']}[1] += {net_name}")
                    script_lines.append(f"{conn['to']}[1] += {net_name}")
                    
                    log.append(f"Added connection from {conn['from']} to {conn['to']} to script")
                    
                except Exception as e:
                    log.append(f"Error adding connection to script: {str(e)}")
                    return False, log, ""
            
            # Add netlist generation
            script_lines.extend([
                "",
                "# Generate netlist",
                "generate_netlist()",
                "",
                "# To use this script:",
                "# 1. Save this to a .py file",
                "# 2. Install SKiDL: pip install skidl",
                "# 3. Run: python this_script.py",
                "# 4. Import the generated netlist in KiCad"
            ])
            
            # Join script lines
            final_script = "\n".join(script_lines)
            
            # Assuming we got here, we succeeded
            success = True
            log.append("Connection script generated successfully")
            
            return success, log, final_script
            
        except Exception as e:
            log.append(f"Error in generating connection script: {str(e)}")
            success = False
            return success, log, ""
            
    def _map_component_to_lib(self, comp_type: str) -> Tuple[str, str]:
        """Map a component type to KiCad library and part"""
        mapping = {
            'R': ('Device', 'R'),
            'C': ('Device', 'C'),
            'L': ('Device', 'L'),
            'D': ('Device', 'D'),
            'Q': ('Device', 'Q_NPN_CBE'),
            'U': ('Device', 'IC'),
            'J': ('Connector', 'Conn_01x02_Male'),
            'SW': ('Switch', 'SW_Push'),
            'LED': ('Device', 'LED'),
            'X': ('Device', 'Crystal'),
            'Y': ('Device', 'Crystal_GND24'),
            'F': ('Device', 'Fuse'),
            'T': ('Device', 'Transformer'),
            'VR': ('Device', 'R_Potentiometer'),
            'TP': ('Connector', 'TestPoint'),
        }
        
        return mapping.get(comp_type, ('Device', 'R'))
            
    def _generate_file_response(self, command: str, execution_log: List[str], success: bool, script: str) -> str:
        """Generate a response message with file content"""
        if success:
            log_lines = "\n- ".join(execution_log)
            return f"""I've generated a KiCad script based on your command:

Command: {command}

Execution Log:
- {log_lines}

Status: Success ✅

Here's the SKiDL script you can use to create these components:

```python
{script}
```

Instructions:
1. Save this script to a .py file
2. Install SKiDL: `pip install skidl`
3. Run: `python your_script.py`
4. The script will generate a netlist file you can import into KiCad
"""
        else:
            log_lines = "\n- ".join(execution_log)
            return f"""I attempted to generate a KiCad script but encountered an issue:

Command: {command}

Execution Log:
- {log_lines}

Status: Failed ❌

Please try a more specific command like "add a 10k resistor" or "connect R1 to C2"
"""

    def _is_create_component_command(self, command: str) -> bool:
        """Check if the command is about creating/adding components"""
        return any(word in command.lower() for word in ["create", "add", "place"])
    
    def _is_connect_command(self, command: str) -> bool:
        """Check if the command is about connecting components"""
        return any(word in command.lower() for word in ["connect", "wire", "link"])
    
    def _get_active_schematic(self):
        """Try to find the active schematic in KiCad"""
        # In a real implementation, this would use wxPython to find the KiCad window
        # and extract the schematic file path
        # For now, let's just return a mock object
        return None
    
    def _extract_components(self, command: str) -> List[Tuple[str, Dict]]:
        """Extract component information from command"""
        components = []
        
        # Look for component patterns - use raw strings for regex patterns
        patterns = {
            'R': r'resistor[s]?\s+(\d+)?\s*(?:k|M|G)?\s*(?:ohm|Ω)?',
            'C': r'capacitor[s]?\s+(\d+)?\s*(?:n|u|p|m)?\s*(?:F|farad)?',
            'L': r'inductor[s]?\s+(\d+)?\s*(?:n|u|m|H)?\s*(?:H|henry)?',
            'D': r'diode[s]?\s+(?:[A-Z0-9]+)?',
            'Q': r'transistor[s]?\s+(?:[A-Z0-9]+)?',
            'U': r'IC[s]?\s+(?:[A-Z0-9]+)?',
            'J': r'connector[s]?\s+(?:[A-Z0-9]+)?',
            'SW': r'switch[s]?\s+(?:[A-Z0-9]+)?',
            'LED': r'LED[s]?\s+(?:[A-Z0-9]+)?',
            'X': r'crystal[s]?\s+(\d+)?\s*(?:MHz|kHz)?',
            'Y': r'oscillator[s]?\s+(\d+)?\s*(?:MHz|kHz)?',
            'F': r'fuse[s]?\s+(\d+)?\s*(?:A|amp)?',
            'T': r'transformer[s]?\s+(?:[A-Z0-9]+)?',
            'VR': r'variable\s+resistor[s]?\s+(\d+)?\s*(?:k|M)?\s*(?:ohm|Ω)?',
            'TP': r'test\s+point[s]?\s+(?:[A-Z0-9]+)?'
        }
        
        # Enhanced patterns to extract values - use raw strings for regex patterns
        value_patterns = {
            'R': r'(\d+(?:\.\d+)?)\s*(?:k|K|M|G)?\s*(?:ohm|Ω|OHM)?',
            'C': r'(\d+(?:\.\d+)?)\s*(?:n|u|µ|p|m|f)?\s*(?:F|farad)?',
        }
        
        try:
            # Look for specific components with values
            for comp_type, pattern in value_patterns.items():
                matches = re.finditer(pattern, command, re.IGNORECASE)
                
                for match in matches:
                    value = match.group(1) if match.group(1) else ""
                    # Extract unit if present (k, M, etc.)
                    units = match.group(0)[match.start(1) + len(value):].strip()
                    
                    # Find the component type in the command
                    component_type_matches = re.finditer(patterns[comp_type], command, re.IGNORECASE)
                    for comp_match in component_type_matches:
                        components.append((comp_type, {'value': value + units}))
                        break
            
            # If no specific values found, use the basic patterns
            if not components:
                for comp_type, pattern in patterns.items():
                    matches = re.finditer(pattern, command, re.IGNORECASE)
                    for match in matches:
                        value = match.group(1) if match.groups() and match.group(1) else ""
                        components.append((comp_type, {'value': value}))
        except Exception as e:
            logger.error(f"Error extracting components: {str(e)}")
            # Return an empty list rather than failing completely
            return []
                
        return components
        
    def _extract_connections(self, command: str) -> List[Dict]:
        """Extract connection information from command"""
        connections = []
        
        # Look for connection patterns
        pattern = r'connect\s+([A-Z0-9]+)\s+to\s+([A-Z0-9]+)'
        matches = re.finditer(pattern, command, re.IGNORECASE)
        
        for match in matches:
            connections.append({
                'from': match.group(1),
                'to': match.group(2),
                'from_pos': '(0, 0)',  # Placeholder
                'to_pos': '(0, 0)'     # Placeholder
            })
            
        return connections
        
    def _get_next_reference(self, comp_type: str) -> str:
        """Get the next reference number for a component type"""
        if comp_type in self.component_counter:
            ref = f"{comp_type}{self.component_counter[comp_type]}"
            self.component_counter[comp_type] += 1
            return ref
        return f"X{self.component_counter['X']}"
        
    def _generate_response(self, command: str, execution_log: List[str], success: bool) -> str:
        """Generate a response message for the user"""
        if success:
            log_lines = "\n- ".join(execution_log)
            return f"""I've processed your KiCad command and executed it:

Command: {command}

Execution Log:
- {log_lines}

Status: Success ✅

The requested changes have been applied to your KiCad schematic.
"""
        else:
            log_lines = "\n- ".join(execution_log)
            return f"""I attempted to process your KiCad command but encountered an issue:

Command: {command}

Execution Log:
- {log_lines}

Status: Failed ❌

To use kicad-skip automation:
1. Make sure kicad-skip is installed: pip install kicad-skip
2. Open your schematic in KiCad before sending commands
3. Try more specific commands like "add a 10k resistor" or "connect R1 to C2"
"""

    def reset_counters(self):
        """Reset all component counters"""
        for key in self.component_counter:
            self.component_counter[key] = 1 