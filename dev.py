"""Dev server: reloads the browser when templates or static files change."""
from livereload import Server

from app import app

app.debug = True
app.config["TEMPLATES_AUTO_RELOAD"] = True

server = Server(app.wsgi_app)
server.watch("templates/")
server.watch("static/")
server.watch("*.py")
server.serve(host="127.0.0.1", port=5000)
