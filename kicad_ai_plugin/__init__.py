#!/usr/bin/env python

"""
KiCad AI Plugin by ALT TAB - Package initialization
This file registers the plugin with KiCad
"""

from .ai_chat import ai_chat_plugin

# Register the plugin with KiCad
ai_chat_plugin.register()

# Plugin registration is handled by ai_chat_plugin instance
# which is created in ai_chat.py 