import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "Knowledgenet API"
author = "Knowledgenet Contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

html_theme = "alabaster"
html_static_path = []