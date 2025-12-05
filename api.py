from flask import Blueprint, jsonify, request

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/sync', methods=['GET'])
def get_sync_status():
    """Retrieve current sync status"""
    return jsonify({
        "status": "Ok",
        "last_sync": "2024-06-01T12:00:00Z",
        "message": "Sync completed successfully"
    }), 200

@api.route('/sync', methods=['POST'])
def trigger_sync():
    """Trigger a sync operation"""
    # TODO: Implement actual sync logic here
    return jsonify({
        "status": "In Progress",
        "message": "Sync initiated"
    }), 202
