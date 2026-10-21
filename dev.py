"""Dev server: reloads the browser when templates or static files change."""
from livereload import Server

from app import app

app.debug = True
app.config["TEMPLATES_AUTO_RELOAD"] = True

server = Server(app.wsgi_app)


def ignore(path):
    parts = path.replace("\\", "/").split("/")
    skip = {".git", "__pycache__", ".venv", "venv", "node_modules"}
    return bool(skip & set(parts)) or path.endswith((".pyc", ".swp", "~"))


server.watch(".", ignore=ignore)
server.serve(host="127.0.0.1", port=5000)
