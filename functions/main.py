
import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# --- PATH CONFIGURATION ---
# This builds an absolute path to the 'Templates' folder, which is necessary for deployment.
template_dir = os.path.abspath(os.path.dirname(__file__))
template_folder = os.path.join(template_dir, 'Templates')

# --- APP INITIALIZATION ---
# Initialize the Flask application, explicitly telling it where to find templates.
app = Flask(__name__, template_folder=template_folder)


# --- DATABASE CONFIGURATION ---
# Use Environment Variable if available (Render), otherwise fallback to the hardcoded string (Local)
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = "postgresql://synergysphere_u:Y646b3HqWq24In3ZDxaM2CRQUU0pIwMV@dpg-d3993tc9c44c73antfkg-a.singapore-postgres.render.com/synergysphere?sslmode=require"

# Ensure the URL starts with 'postgresql://' for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# REQUIRED for Render production stability
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "sslmode": "require"
    },
    "pool_pre_ping": True, # Checks connection health before using it
}

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
# These classes define the structure of your database tables.

project_members = db.Table('project_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True)
)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")
    members = db.relationship('User', secondary=project_members, lazy='subquery',
                              backref=db.backref('projects', lazy=True))
    messages = db.relationship('Message', backref='project', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'tasks': [task.to_dict() for task in self.tasks],
            'members': [member.to_dict_simple() for member in self.members],
            'messages': [message.to_dict() for message in self.messages if message.parent_id is None]
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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    messages = db.relationship('Message', backref='author', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'projects': [project.id for project in self.projects]
        }
    
    def to_dict_simple(self):
        """A simpler representation of the User, excluding projects to avoid circular deps."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'user': self.author.to_dict_simple(),
            'project_id': self.project_id,
            'parent_id': self.parent_id,
            'replies': [reply.to_dict() for reply in self.replies]
        }

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    link = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_read': self.is_read,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'link': self.link
        }

# --- HELPER FUNCTIONS ---
def create_notification(user, content, link):
    """Creates a notification for a specific user."""
    notification = Notification(user_id=user.id, content=content, link=link)
    db.session.add(notification)

# --- WEB & API ROUTES ---
# These are the endpoints for your application.
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = Project.query.order_by(Project.id).all()
    return jsonify([project.to_dict() for project in projects])

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    return jsonify(project.to_dict())

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Project name is required'}), 400
    
    new_project = Project(name=data['name'])
    
    creator_id = data.get('creator_id')
    if creator_id:
        user = User.query.get(creator_id)
        if user:
            new_project.members.append(user)

    db.session.add(new_project)
    db.session.commit()
    return jsonify(new_project.to_dict()), 201

@app.route('/api/projects/<int:project_id>/members', methods=['POST'])
def add_project_member(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    if not data or not data.get('user_id'):
        return jsonify({'error': 'User ID is required'}), 400

    user = User.query.get_or_404(data['user_id'])
    
    if user not in project.members:
        project.members.append(user)
        notification_content = f"You have been added to the project '{project.name}'."
        create_notification(user, notification_content, f"#/projects/{project.id}")
        db.session.commit()
        
    return jsonify(project.to_dict()), 201

@app.route('/api/projects/<int:project_id>/messages', methods=['GET'])
def get_messages(project_id):
    project = Project.query.get_or_404(project_id)
    messages = [msg.to_dict() for msg in project.messages if msg.parent_id is None]
    return jsonify(messages)

@app.route('/api/projects/<int:project_id>/messages', methods=['POST'])
def post_message(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    if not data or not data.get('content') or not data.get('user_id'):
        return jsonify({'error': 'Content and user_id are required'}), 400

    user = User.query.get_or_404(data['user_id'])
    
    new_message = Message(
        content=data['content'],
        user_id=user.id,
        project_id=project.id,
        parent_id=data.get('parent_id')
    )
    db.session.add(new_message)

    # Notify other project members
    for member in project.members:
        if member.id != user.id:
            notification_content = f"New message in '{project.name}' by {user.name}."
            create_notification(member, notification_content, f"#/projects/{project.id}")

    db.session.commit()
    return jsonify(new_message.to_dict()), 201


@app.route('/api/projects/<int:project_id>/tasks', methods=['POST'])
def create_task(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': 'Task content is required'}), 400
    new_task = Task(content=data['content'], project_id=project.id)
    db.session.add(new_task)

    # Notify project members
    for member in project.members:
        notification_content = f"New task '{new_task.content}' added to '{project.name}'."
        create_notification(member, notification_content, f"#/projects/{project.id}")

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

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = request.args.get('user_id')
    if not user_id:
        # In a real session-based app, you'd get this from the session
        return jsonify({'error': 'user_id is required'}), 400
    
    user = User.query.get_or_404(user_id)
    notifications = user.notifications.filter_by(is_read=False).order_by(Notification.timestamp.desc()).all()
    return jsonify([n.to_dict() for n in notifications])

@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    # Here you would typically also check if the notification belongs to the current logged-in user
    notification.is_read = True
    db.session.commit()
    return jsonify(notification.to_dict())

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        user = User(email=data['email'], name=data['name'], google_id=data['uid'])
        db.session.add(user)
        db.session.commit()
    return jsonify(user.to_dict()), 200

@app.route('/api/users', methods=['GET'])
def get_users():
    """Fetches all users."""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

# This command creates the database tables if they don't exist when the app starts
with app.app_context():
    db.create_all()
