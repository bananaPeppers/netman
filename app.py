from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "NetMan IDS/IPS Server is running!"

@app.route("/health")
def health():
    return {"status": "healthy"}
