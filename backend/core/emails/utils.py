import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Setup Jinja2 environment
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

def render_template(template_name: str, **kwargs) -> str:
    """Render a Jinja2 template with context variables"""
    template = env.get_template(template_name)
    return template.render(**kwargs)
