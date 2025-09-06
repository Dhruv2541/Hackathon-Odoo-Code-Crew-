import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# Initialize the Flask application
app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
# Sets up the base directory for the database file
basedir = os.path.abspath(os.path.dirname(__file__))

# Configure the connection to your PostgreSQL database.
# IMPORTANT: Replace the placeholders with your actual PostgreSQL credentials from the setup guide.
# Format: 'postgresql://USERNAME:PASSWORD@HOSTNAME/DATABASE_NAME'
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'postgresql://team_user:dp686@localhost/synergysphere'

# This silences a deprecation warning
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database extension
db = SQLAlchemy(app)


# --- DATABASE MODELS ---
# These classes define the structure of your database tables.

class Project(db.Model):
    """Represents a project board."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # This creates a relationship so you can easily access tasks from a project
    # The `cascade="all, delete-orphan"` part means if a project is deleted, its tasks are also deleted.
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """Converts the Project object to a dictionary for easy JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'tasks': [task.to_dict() for task in self.tasks]
        }

class Task(db.Model):
    """Represents a single task within a project."""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    # This links a task to a project using a foreign key
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    def to_dict(self):
        """Converts the Task object to a dictionary."""
        return {
            'id': self.id,
            'content': self.content,
            'is_done': self.is_done
        }


# --- WEB ROUTES (Views) ---
# This route serves the main HTML page of your application.
@app.route('/')
def index():
    """Renders the main frontend page."""
    return render_template('index.html')


# --- API ENDPOINTS ---
# These routes are for your frontend JavaScript to interact with the database.

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Fetches all projects and their tasks from the database."""
    projects = Project.query.order_by(Project.id).all()
    # Convert the list of project objects into a list of dictionaries
    return jsonify([project.to_dict() for project in projects])

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Creates a new project."""
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Project name is required'}), 400

    new_project = Project(name=data['name'])
    db.session.add(new_project)
    db.session.commit()
    return jsonify(new_project.to_dict()), 201

@app.route('/api/projects/<int:project_id>/tasks', methods=['POST'])
def create_task(project_id):
    """Creates a new task for a specific project."""
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
    """Updates a task, e.g., to mark it as done."""
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    # Toggle the 'is_done' status
    task.is_done = data.get('is_done', task.is_done)
    db.session.commit()
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Deletes a task."""
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted successfully'})

# This command creates the database tables if they don't exist when the app starts
with app.app_context():
    db.create_all()

# This is the standard entry point for running the Flask app
if __name__ == '__main__':
    app.run(debug=True)