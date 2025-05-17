from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route("/health")
def health():
    return jsonify(dict(status="OK")), 200

@app.route('/count', methods=['GET'])
def count():
    try:
        count = db.songs.count_documents({})
        return jsonify({"count": count})
    except OperationFailure as e:
        app.logger.error(f"Error counting documents: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/song', methods=['GET'])
def songs():
    try:
        data = db.songs.find({})
        songs = parse_json(data)
        return jsonify({"songs": songs}), 200
    except OperationFailure as e:
        app.logger.error(f"Error retrieving songs: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/song/<id>', methods=['GET'])
def get_song_by_id(id):
    song_id = int(id)
    try:
        data = db.songs.find_one({"id": song_id})
        # print data
        if data is None:
            return jsonify({"message": "song with id not found"}), 404
        song = parse_json(data)
        return jsonify(song), 200
    except OperationFailure as e:
        app.logger.error(f"Error retrieving song by id: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/song', methods=['POST'])
def create_song():
    try:
        song = request.get_json()
        if not song:
            return jsonify({"message": "No data provided"}), 400
        if db.songs.find_one({"id": song['id']}):
            return jsonify({"Message": f"song with id {song['id']} already present"}), 302
        result: InsertOneResult = db.songs.insert_one(song)
        return jsonify({"message": "Song created", "id": str(result.inserted_id)}), 201
    except OperationFailure as e:
        app.logger.error(f"Error creating song: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    song_id = int(id)
    newsongdata = request.get_json()
    try:
        data = db.songs.find_one({"id": song_id})
        if data is None:
            return jsonify({"message": "song with id not found"}), 404
        if not newsongdata:
            return jsonify({"message": "No data provided"}), 400
        if (
            data["lyrics"] == newsongdata["lyrics"]
            and data["title"] == newsongdata["title"]
        ):
            return jsonify({"song found, but nothing updated"}), 200
        result = db.songs.update_one({"id": song_id}, {"$set": newsongdata})
        if result.matched_count == 0:
            return jsonify({"message": "song not found"}), 404
        return jsonify({"message": "Song updated"}), 200
    except OperationFailure as e:
        app.logger.error(f"Error updating song: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    song_id = int(id)
    try:
        result = db.songs.delete_one({"id": song_id})
        if result.deleted_count == 0:
            return jsonify({"message": "song not found"}), 404
        return "", 204
    except OperationFailure as e:
        app.logger.error(f"Error deleting song: {str(e)}")
        return jsonify({"error": str(e)}), 500