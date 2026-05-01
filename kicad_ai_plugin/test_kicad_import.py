#!/usr/bin/env python
import os
import sys
import base64
from kicad_file_processor import is_kicad_file, extract_kicad_file_info

# Example usage
def test_with_example_file():
    # Create an example KiCad file
    example_content = """
(kicad_pcb (version 20211014) (generator pcbnew)

  (general
    (thickness 1.6)
  )

  (paper "A4")
  
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
    (44 "Edge.Cuts" user)
  )
  
  (footprint "Resistor_SMD:R_0805_2012Metric" (layer "F.Cu")
    (tstamp 5c1c28f1-34e1-4347-abb2-eec8fd0aa3c0)
    (property "Reference" "R1" (id 0) (at 0 1.7 0)
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (property "Value" "10k" (id 1) (at 0 -1.65 0)
      (effects (font (size 1 1) (thickness 0.15)))
    )
  )
)
    """
    
    # Create a temp file
    temp_file = "example.kicad_pcb"
    with open(temp_file, "w") as f:
        f.write(example_content)
    
    # Now process the file
    file_ext = ".kicad_pcb"
    
    # Check if KiCad file
    kicad_file = is_kicad_file(file_ext)
    print(f"Is KiCad file: {kicad_file}")
    
    if kicad_file:
        # Extract KiCad info
        info = extract_kicad_file_info(temp_file, file_ext, example_content)
        print("\nKiCad File Information:")
        for key, value in info.items():
            print(f"{key}: {value}")
    
    # Clean up
    os.remove(temp_file)

if __name__ == "__main__":
    test_with_example_file() 