from db_config import Config
from flask import Flask
import os
from werkzeug.serving import WSGIRequestHandler
from flask_sqlalchemy import SQLAlchemy

UPLOAD_FOLDER = os.path.join('static', 'avatars')
WSGIRequestHandler.protocol_version = "HTTP/1.1"
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.from_object(Config)
app.config['JSON_AS_ASCII'] = False
db = SQLAlchemy(app)
