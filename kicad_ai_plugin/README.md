# KiCad Chatbot by ALT TAB and Stefan Jancic

An AI-powered assistant plugin for KiCad that provides a chat interface to help with PCB and schematic design tasks.

## Features

- Chat interface for interacting with AI models
- Upload and analyze KiCad files
- Query design rules, component selection, and layout tips
- Save and manage multiple conversations
- Works with both PCB and schematic editors
- Drag and drop file import options inside the plugin

## Installation

### Option 1: Direct Download

1. Download the latest release ZIP file from kicad.altstab.rs
2. Extract the ZIP file to your KiCad plugins directory:
   - Windows: `C:\Users\<username>\Documents\KiCad\9.0\scripting\plugins\`
   - macOS: `~/Documents/KiCad/9.0/scripting\plugins\`
   - Linux: `~/.kicad/9.0/scripting/plugins/`
3. Restart KiCad

### Option 2: Manual Installation

1. Clone the repository (private repository, access must be granted):
   ```
   git clone https://github.com/jancicS/kicad-chatbot.git
   ```
2. Install the required dependencies:
   ```
   cd kicad-chatbot
   pip install -r requirements.txt
   ```
3. Copy the plugin to your KiCad plugins directory:
   - Windows: Copy to `C:\Users\<username>\Documents\KiCad\9.0\scripting\plugins\`
   - macOS: Copy to `~/Documents/KiCad/9.0/scripting/plugins/`
   - Linux: Copy to `~/.kicad/9.0/scripting/plugins/`
4. Restart KiCad

## File Support

The plugin can extract and analyze content from various file types:

- KiCad files (.kicad_pcb, .kicad_sch, .kicad_pro, .net, .lib, etc.)
- Text files (.txt, .md, .py, .js, .html, .css, .json, etc.)
- PDF files (requires PyPDF2)
- Word documents (.docx, requires python-docx)
- Images (can be viewed by GPT-4 Vision models)

## Configuration

### API Key Setup

Before you can use the chatbot, you need to configure your OpenAI API key:

1. Launch KiCad and open the PCB or Schematic editor
2. Click on the "KiCad Chatbot by ALT TAB" button in the toolbar
3. Click on the "Add API Key" button in the chat interface
4. Enter your OpenAI API key and click "Save"

You can get an API key from [OpenAI's platform](https://platform.openai.com/api-keys).

## Usage

1. Click on the "KiCad Chatbot by ALT TAB" button in the KiCad toolbar
2. Type your question or query in the input box
3. Click "Send" or press Enter
4. You can upload KiCad files by dragging and dropping them into the chat window
5. Use the model selector to switch between available AI models

## Examples

- "What are the best practices for routing high-speed differential pairs?"
- "How should I lay out a power supply circuit for low noise?"
- "Can you review this schematic for potential issues?" (upload a .kicad_sch file)
- "What's the appropriate trace width for a 2A current?"

## Support

For issues, feature requests, or questions, please visit kicad.altstab.rs or contact the developer on GitHub.

## License

**Proprietary Software - All Rights Reserved**

This software is the property of Stefan Jancic (ALT TAB) and is protected by copyright law and international treaties.

Unauthorized reproduction, distribution, or use of this software, in whole or in part, may result in civil and criminal penalties, and will be prosecuted to the maximum extent possible under law.

Use of this software is subject to the terms and conditions specified by the author. For licensing inquiries, please contact Stefan Jancic via GitHub or ALT TAB website.

### PROPRIETARY SOFTWARE LICENSE AGREEMENT

**KiCad Chatbot by ALT TAB**

Copyright (c) 2024 Stefan Jancic (ALT TAB)
All Rights Reserved

1. **GRANT OF LICENSE**
   This software is licensed, not sold. Stefan Jancic (ALT TAB) grants you a non-transferable,
   non-exclusive license to use the software subject to the terms and conditions of this agreement.

2. **OWNERSHIP**
   This software is owned and copyrighted by Stefan Jancic (ALT TAB). Your license confers no title
   or ownership in the software and is not a sale of any rights in the software.

3. **RESTRICTIONS**
   You may NOT:
   a. Distribute, share, sublicense, lend, lease, or rent this software;
   b. Reverse engineer, decompile, disassemble, or create derivative works from this software;
   c. Remove or alter any copyright, trademark, or other proprietary notices;
   d. Use the software for commercial purposes without explicit written permission.

4. **TERMINATION**
   This license is effective until terminated. Your rights under this license will terminate
   automatically without notice if you fail to comply with any term of this agreement.

5. **DISCLAIMER OF WARRANTY**
   The software is provided "AS IS" without warranty of any kind, either express or implied,
   including, but not limited to, the implied warranties of merchantability and fitness for a
   particular purpose. The entire risk as to the quality and performance of the software is with you.

6. **LIMITATION OF LIABILITY**
   In no event shall Stefan Jancic (ALT TAB) be liable for any damages whatsoever arising out of
   the use of or inability to use this software.

7. **GOVERNING LAW**
   This agreement shall be governed by the laws of Serbia.

For licensing inquiries, permission requests, or to report unauthorized distribution,
please contact Stefan Jancic:

GitHub: https://github.com/jancicS
Website: https://alttab.rs 