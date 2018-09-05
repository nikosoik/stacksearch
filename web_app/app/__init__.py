from flask import Flask

app = Flask(__name__)

from app import routes

app.run('0.0.0.0', 5080, debug=False)
