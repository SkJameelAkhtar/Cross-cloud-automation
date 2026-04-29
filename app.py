from flask import Flask, request
import datetime

app = Flask(__name__)

DATA_FILE = "data.txt"

@app.route("/")
def home():
    return "Backup Demo App Running!"

@app.route("/write")
def write():
    with open(DATA_FILE, "a") as f:
        f.write(f"Entry at {datetime.datetime.now()}\n")
    return "Data written!"

@app.route("/read")
def read():
    try:
        with open(DATA_FILE, "r") as f:
            return "<br>".join(f.readlines())
    except:
        return "No data yet."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
