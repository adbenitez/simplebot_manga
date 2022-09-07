"""Templates"""

from jinja2 import Environment, PackageLoader, Template, select_autoescape

env = Environment(
    loader=PackageLoader(__name__.split(".", maxsplit=1)[0], "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def get_template(name: str) -> Template:
    return env.get_template(name)
