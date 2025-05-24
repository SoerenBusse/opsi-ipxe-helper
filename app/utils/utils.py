from jinja2 import Environment


def render_error_template(jinja_environment: Environment, message: str) -> str:
    template = jinja_environment.get_template("error.menu.ipxe")
    rendered = template.render(error_message=message)

    return rendered
