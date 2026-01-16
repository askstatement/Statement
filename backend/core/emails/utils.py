import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8765")

# Setup Jinja2 environment
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

env.globals["BASE_URL"] = BASE_URL

def render_template(template_name: str, **kwargs) -> str:
    """Render a Jinja2 template with context variables"""
    template = env.get_template(template_name)
    return template.render(**kwargs)
