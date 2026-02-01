from flask import Flask
import os

from app.webhook.routes import webhook
from app.extensions import mongo


# Creating our flask app
def create_app():

    app = Flask(__name__)
    db_uri = os.getenv("DB_URI")
    if not db_uri:
        raise RuntimeError("DB_URI environment variable is not set.")
        
    app.config["MONGO_URI"] = db_uri

    mongo.init_app(app)
    
    # registering all the blueprints
    app.register_blueprint(webhook)
    
    return app
