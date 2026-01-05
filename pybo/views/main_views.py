from flask import Blueprint, url_for, session
from werkzeug.utils import redirect


bp = Blueprint('main',__name__, url_prefix='/')


@bp.route('/hello')
def hello_pybo():
    return 'Hello, Pybo!'


@bp.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    return redirect(url_for('question._list'))
