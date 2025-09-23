# --- IMPORTS ---
# Your original imports
import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# New imports required for Cloud Functions
from firebase_admin import initialize_app
from firebase_functions import https_fn

# --- INITIALIZATION ---
# This is required for the function to run in the Firebase environment
initialize_app()

# Initialize the Flask application (your original code)
app = Flask(__name__)


# --- DATABASE CONFIGURATION (IMPROVED) ---
# This is the most important change.
# Replace the placeholder text with the "External Database URL" you copied from Render.
DATABASE_URL = "postgresql://synergysphere_u:Y646b3HqWq24In3ZDxaM2CRQUU0pIwMV@dpg-d3993tc9c44c73antfkg-a.singapore-postgres.render.com/synergysphere"

# Check if the URL is set, otherwise use a default that will intentionally fail
# This prevents accidentally connecting to a non-existent database.
if not DATABASE_URL:
    raise ValueError("No database URL has been provided. Please set it in your code.")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database extension
db = SQLAlchemy(app)


# --- DATABASE MODELS ---
# Your original database model classes are unchanged.
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'tasks': [task.to_dict() for task in self.tasks]
        }

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_done': self.is_done
        }


# --- WEB & API ROUTES ---
# All your original routes are unchanged.
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = Project.query.order_by(Project.id).all()
    return jsonify([project.to_dict() for project in projects])

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Project name is required'}), 400
    new_project = Project(name=data['name'])
    db.session.add(new_project)
    db.session.commit()
    return jsonify(new_project.to_dict()), 210

@app.route('/api/projects/<int:project_id>/tasks', methods=['POST'])
def create_task(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': 'Task content is required'}), 400
    new_task = Task(content=data['content'], project_id=project.id)
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    task.is_done = data.get('is_done', task.is_done)
    db.session.commit()
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted successfully'})

# --- NOTE ON DATABASE CREATION ---
# The `db.create_all()` and `app.run()` blocks are correctly removed for deployment.
# To create your tables for the first time, you will need to run a separate Python
# script from your local machine that connects to the Render database.


# --- CLOUD FUNCTION WRAPPER ---
# This is the required entry point for Firebase. It wraps your entire Flask app.
@https_fn.on_request()
def odoocrew(req: https_fn.Request) -> https_fn.Response:
    with app.request_context(req.environ):
        return app.full_dispatch_request()