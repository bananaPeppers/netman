from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "NetMan Auto Deployment Test - Version 2!"

@app.route("/health")
def health():
    return {"status": "healthy"}
