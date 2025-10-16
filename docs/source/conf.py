"""Sphinx configuration file for homeassistant_powersensor documentation."""

import sys
from pathlib import Path

# Add the package to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "custom_components"))
print(project_root)

# Project information
project = "homeassistant-powersensor"
copyright = "2025, DiUS"
author = "Powersensor Team!"

html_favicon = "_static/powersensor-logo.png"
html_logo = "_static/powersensor-logo.png"


release = "0.0.1"

version = ".".join(release.split(".")[:2])

# Extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx.ext.autosummary"
]

# Napoleon settings (for Google and NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# HTML theme
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = []


# Output file base name for HTML help builder
htmlhelp_basename = "homeassistant_powersensor_doc"

# Options for LaTeX output
latex_elements = {}
latex_documents = [
    ("index", "homeassistant_powersensor.tex", "homeassistant_powersensor Documentation", "Your Name", "manual"),
]

# Options for manual page output
man_pages = [
    ("index", "homeassistant_powersensor", "homeassistant_powersensor Documentation", [author], 1)
]

# Options for Texinfo output
texinfo_documents = [
    (
        "index",
        "homeassistant_powersensor",
        "homeassistant_powersensor Documentation",
        author,
        "homeassistant_powersensor",
        "One line description of project.",
        "Miscellaneous",
    ),
]
