

from flask import Flask, request
from views import main_blueprint
from auth import auth_blueprint
from models import db, User, Visit
from flask_login import LoginManager
import os
import dotenv

dotenv.load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres", "postgresql", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprint for routes
app.register_blueprint(main_blueprint)
app.register_blueprint(auth_blueprint)

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.errorhandler(404)
def not_found(e):
    try:
        visit = Visit(page=f'404: {request.path} not found', user=None)
        db.session.add(visit)
        db.session.commit()
    except Exception:
        db.session.rollback()
    return f"404 - Page not found: {request.path}", 404

@app.errorhandler(500)
def server_error(e):
    try:
        visit = Visit(page=f'500: {str(e)[:150]}', user=None)
        db.session.add(visit)
        db.session.commit()
    except Exception:
        db.session.rollback()
    return "500 - Internal server error", 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)