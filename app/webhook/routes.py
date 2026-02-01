from datetime import datetime
from flask import Blueprint, json, render_template, request
from flask_pymongo import DESCENDING
from app.extensions import mongo
from enum import Enum
from flask import jsonify

webhook = Blueprint('Webhook', __name__, url_prefix='/webhook')

class GitHubEventType(Enum):
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    MERGE = "merge"

@webhook.route('/receiver', methods=["POST"])
def receiver():
    if request.headers['Content-Type'] != 'application/json':
        return {"error": "Invalid content type"}, 400

    event = request.headers.get('X-Github-Event')
    
    if event == 'pull_request':
        if request.json.get("action") == "opened":
            # handle open pull request event
            payload = request.json
            webhook_event = {
                "request_id": payload["pull_request"]["id"],
                "author": payload["pull_request"]["user"]["login"],
                "action": GitHubEventType.PULL_REQUEST.value,
                "from_branch": payload["pull_request"]["head"]["ref"],
                "to_branch": payload["pull_request"]["base"]["ref"],
                "timestamp": formatDatetime(payload["pull_request"]["created_at"]),
            }
            mongo.db.webhookEvents.insert_one(webhook_event)
        elif request.json.get("action") == "closed" and request.json["pull_request"].get("merged"):
            # handle merged pull request event
            payload = request.json
            webhook_event = {
                "request_id": payload["pull_request"]["id"],
                "author": payload["pull_request"]["user"]["login"],
                "action": GitHubEventType.MERGE.value,
                "from_branch": payload["pull_request"]["head"]["ref"],
                "to_branch": payload["pull_request"]["base"]["ref"],
                "timestamp": formatDatetime(payload["pull_request"]["merged_at"]),
            }
            mongo.db.webhookEvents.insert_one(webhook_event)
        
        return jsonify(webhook_event), 200
        
    elif event == 'push':
        payload = request.json
        webhook_event = {
            "request_id": payload["head_commit"]["id"],
            "author": payload["pusher"]["name"],
            "action": GitHubEventType.PUSH.value,
            "from_branch": None,
            "to_branch": payload["ref"],
            "timestamp": formatDatetime(payload["head_commit"]["timestamp"]),
        }
        mongo.db.webhookEvents.insert_one(webhook_event)

        return jsonify(webhook_event), 200
    else:
        return {"error": "Unsupported event type"}, 400


@webhook.route('/events', methods=["GET"])
def get_events():
    events = mongo.db.webhookEvents.find().sort("timestamp", DESCENDING)
    
    result = []
    for event in events:
        event["_id"] = str(event["_id"]) # convert monogodb "ObjectId" to str
        event["timestamp"] = event["timestamp"].isoformat() # convert datetime to iso format
        result.append(event)
        
    return jsonify(result), 200

@webhook.route('/', methods=["GET"])
def index():
    return render_template("index.html")

@webhook.route('/status', methods=["GET"])
def status():
    mongo.cx.admin.command("ping") 
    result = mongo.db.healthchecks.update_one(
            {"_id": "status"},
            {"$set": {"ts": datetime.utcnow()}},
            upsert=True,
        )
    return {
        "status": "ok",
        "db": mongo.db.name,
        "mock_write": bool(result.upserted_id or result.modified_count),
    }, 200


def formatDatetime(dt_str):
    dt_object = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return dt_object