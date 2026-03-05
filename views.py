import random
import json
from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask_login import login_required, current_user
from models import db, Task, User, Visit, Waitlist
from sqlalchemy import func as sqlfunc
import datetime

# Create a blueprint
main_blueprint = Blueprint('main', __name__)


def log_visit(page, user_id):
    """Log a visit to a page by a user."""
    visit = Visit(page=page, user=user_id)
    db.session.add(visit)
    db.session.commit()


###############################################################################
# Routes
###############################################################################


@main_blueprint.route('/', methods=['GET'])
def index():
    log_visit(page='index', user_id=current_user.id if current_user.is_authenticated else None)

    # print all visits
    visits = Visit.query.all()
    for visit in visits:
        print(f"Visit: {visit.page}, User ID: {visit.user}, Timestamp: {visit.timestamp}")

    return render_template('index.html')

@main_blueprint.route('/invitation', methods=['GET', 'POST'])
def invitation():
    if request.method == 'GET':
        log_visit(page='invitation', user_id=current_user.id if current_user.is_authenticated else None)

    if request.method == 'POST':
        email = request.form['email']
        # Save email to the waitlist if not already present
        if not Waitlist.query.filter_by(email=email).first():
            entry = Waitlist(email=email)
            db.session.add(entry)
            db.session.commit()
        log_visit(page='waitlist', user_id=current_user.id if current_user.is_authenticated else None)
    return render_template('invitation.html')


@main_blueprint.route('/todo', methods=['GET', 'POST'])
@login_required
def todo():
    log_visit(page='todo', user_id=current_user.id)
    return render_template('todo.html')


@main_blueprint.route('/dashboard', methods=['GET', 'POST'])
# @login_required
def dashboard():
    today = datetime.datetime.now().date()
    week_start = datetime.datetime.now() - datetime.timedelta(days=6)

    # --- Stats cards ---
    visits_today = Visit.query.filter(
        sqlfunc.date(Visit.timestamp) == today
    ).count()

    new_users = Visit.query.filter(
        Visit.page == 'signup',
        Visit.timestamp >= week_start
    ).count()

    waitlist_this_week = Waitlist.query.filter(
        Waitlist.timestamp >= week_start
    ).count()

    total_users = User.query.count()

    # --- DB stats ---
    total_visits = Visit.query.count()
    total_tasks = Task.query.count()
    users = User.query.all()
    waitlist = Waitlist.query.all()

    # --- Pages we actively track (not errors) ---
    TRACKED_PAGES = ['index', 'invitation', 'waitlist', 'todo', 'dashboard',
                     'signup-page', 'signup', 'login', 'task-create',
                     'task-toggle', 'task-delete', 'try']

    # --- Recent 15 legitimate visits (newest first, errors excluded) ---
    recent_visits = (
        Visit.query
        .filter(Visit.page.in_(TRACKED_PAGES))
        .order_by(Visit.timestamp.desc())
        .limit(15)
        .all()
    )

    # --- Recent 15 errors (newest first) ---
    recent_errors = (
        Visit.query
        .filter(~Visit.page.in_(TRACKED_PAGES))
        .order_by(Visit.timestamp.desc())
        .limit(15)
        .all()
    )

    # --- Chart labels: last 7 days with today as last ---
    chart_labels = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        chart_labels.append(day.strftime('%a'))

    # --- Index page visits: this week vs last week (daily) ---
    week_visits = []
    two_week_visits = []
    for i in range(6, -1, -1):
        this_day = today - datetime.timedelta(days=i)
        prev_day = this_day - datetime.timedelta(days=7)
        week_visits.append(
            Visit.query.filter(Visit.page == 'index',
                               sqlfunc.date(Visit.timestamp) == this_day).count()
        )
        two_week_visits.append(
            Visit.query.filter(Visit.page == 'index',
                               sqlfunc.date(Visit.timestamp) == prev_day).count()
        )

    # --- New signups per day: this week vs last week ---
    week_notes = []
    two_week_notes = []
    for i in range(6, -1, -1):
        this_day = today - datetime.timedelta(days=i)
        prev_day = this_day - datetime.timedelta(days=7)
        week_notes.append(
            Visit.query.filter(Visit.page == 'signup',
                               sqlfunc.date(Visit.timestamp) == this_day).count()
        )
        two_week_notes.append(
            Visit.query.filter(Visit.page == 'signup',
                               sqlfunc.date(Visit.timestamp) == prev_day).count()
        )

    # --- Page visits today for bar chart (tracked pages only) ---
    page_visits_query = (
        db.session.query(Visit.page, sqlfunc.count(Visit.id))
        .filter(
            sqlfunc.date(Visit.timestamp) == today,
            Visit.page.in_(TRACKED_PAGES)
        )
        .group_by(Visit.page)
        .all()
    )
    page_visit_labels = json.dumps([row[0] for row in page_visits_query])
    page_visits_data = json.dumps([row[1] for row in page_visits_query])

    # --- Productivity change (index visits this week vs last week) ---
    total_this_week = sum(week_visits)
    total_last_week = sum(two_week_visits)
    if total_last_week > 0:
        productivity_change = round(((total_this_week - total_last_week) / total_last_week) * 100, 1)
    elif total_this_week > 0:
        productivity_change = 100
    else:
        productivity_change = 0

    # --- Users change (new signups this week vs last week) ---
    total_new_this = sum(week_notes)
    total_new_last = sum(two_week_notes)
    if total_new_last > 0:
        users_change = round(((total_new_this - total_new_last) / total_new_last) * 100, 1)
    elif total_new_this > 0:
        users_change = 100
    else:
        users_change = 0

    return render_template('admin.html',
                           date=datetime.datetime.now().strftime("%B %d, %Y"),
                           total_users=total_users,
                           new_users=new_users,
                           visits_today=visits_today,
                           waitlist_this_week=waitlist_this_week,
                           productivity_change=productivity_change,
                           users_change=users_change,
                           visits=recent_visits,
                           errors=recent_errors,
                           total_visits=total_visits,
                           total_tasks=total_tasks,
                           users=users,
                           waitlist=waitlist,
                           chart_week=json.dumps(chart_labels),
                           week_notes=week_notes,
                           two_week_notes=two_week_notes,
                           week_visits=week_visits,
                           two_week_visits=two_week_visits,
                           page_visits=page_visits_data,
                           page_visit_labels=page_visit_labels
                           )



@main_blueprint.route('/api/v1/tasks', methods=['GET'])
@login_required
def api_get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return {
        "tasks": [task.to_dict() for task in tasks]
    }


@main_blueprint.route('/api/v1/tasks', methods=['POST'])
@login_required
def api_create_task():
    data = request.get_json()
    new_task = Task(title=data['title'], user_id=current_user.id)
    db.session.add(new_task)
    db.session.commit()
    log_visit(page='task-create', user_id=current_user.id)
    return {
        "task": new_task.to_dict()
    }, 201


@main_blueprint.route('/api/v1/tasks/<int:task_id>', methods=['PATCH'])
@login_required
def api_toggle_task(task_id):
    task = Task.query.get(task_id)

    if task is None:
        return {"error": "Task not found"}, 404

    task.toggle()
    db.session.commit()
    log_visit(page='task-toggle', user_id=current_user.id)
    return {"task": task.to_dict()}, 200


@main_blueprint.route('/remove/<int:task_id>')
@login_required
def remove(task_id):
    task = Task.query.get(task_id)

    if task is None:
        return redirect(url_for('main.todo'))

    db.session.delete(task)
    db.session.commit()
    log_visit(page='task-delete', user_id=current_user.id)
    return redirect(url_for('main.todo'))