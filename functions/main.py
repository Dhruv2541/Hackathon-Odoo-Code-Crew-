# --- IMPORTS ---
import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# --- PATH CONFIGURATION ---
# This builds an absolute path to the 'Templates' folder, which is necessary for deployment.
template_dir = os.path.abspath(os.path.dirname(__file__))
template_folder = os.path.join(template_dir, 'Templates')

# --- APP INITIALIZATION ---
# Initialize the Flask application, explicitly telling it where to find templates.
app = Flask(__name__, template_folder=template_folder)


# --- DATABASE CONFIGURATION ---
# This connects to your Render PostgreSQL database.
DATABASE_URL = "postgresql://synergysphere_u:Y646b3HqWq24In3ZDxaM2CRQUU0pIwMV@dpg-d3993tc9c44c73antfkg-a.singapore-postgres.render.com/synergysphere"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database extension with the app
db = SQLAlchemy(app)


# --- DATABASE MODELS ---
# These classes define the structure of your database tables.
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

# --- DATABASE MODELS ---
# ... (Project and Task classes are here) ...

class Task(db.Model):
    # ... existing code ...
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_done': self.is_done
        }

# --- ADD THE USER MODEL HERE ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))

    def to_dict(self):
        return {'id': self.id, 'email': self.email, 'name': self.name}

# --- WEB & API ROUTES ---
# ... rest of your code ...
# --- WEB & API ROUTES ---
# These are the endpoints for your application.
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
    return jsonify(new_project.to_dict()), 201

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

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        user = User(email=data['email'], name=data['name'], google_id=data['uid'])
        db.session.add(user)
        db.session.commit()
    return jsonify(user.to_dict()), 200

# --- TEMPORARY INITIALIZATION ROUTE ---
@app.route('/api/init-db')
def init_db():
    try:
        # This command creates the Project, Task, and User tables in PostgreSQL
        db.create_all()
        return "Database tables created successfully! You can now use Google Login.", 200
    except Exception as e:
        return f"Error: {str(e)}", 500
