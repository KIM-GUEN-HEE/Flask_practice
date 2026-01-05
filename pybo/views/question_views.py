from datetime import datetime

from flask import Blueprint, render_template, request, url_for, session, abort
from werkzeug.utils import redirect
from .. import db

from pybo.models import Question, User

from pybo.forms import QuestionForm, AnswerForm
from pybo.login_required import login_required

bp = Blueprint('question', __name__, url_prefix='/question')

@bp.route('/list/')
@login_required
def _list():
    question_list = Question.query.order_by(Question.create_date.desc())
    return render_template('question/question_list.html', question_list=question_list)


@bp.route('/detail/<int:question_id>/')
@login_required
def detail(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)
    return render_template('question/question_detail.html', question=question, form= form)

@bp.route('/create/', methods=('GET','POST'))
@login_required
def create():
    form = QuestionForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(username=session.get('username')).first()
        question = Question(subject=form.subject.data, content=form.content.data, create_date=datetime.now(), user_id=user.id)
        db.session.add(question)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('question/question_form.html', form=form)

@bp.route('/modify/<int:question_id>/', methods=('GET', 'POST'))
@login_required
def modify(question_id):
    question = Question.query.get_or_404(question_id)
    user = User.query.filter_by(username=session.get('username')).first()
    
    # 본인이 작성한 게시글이 아니면 접근 불가
    if question.user_id != user.id:
        abort(403)
    
    form = QuestionForm()
    if request.method == 'POST' and form.validate_on_submit():
        form.populate_obj(question)
        question.create_date = datetime.now()
        db.session.commit()
        return redirect(url_for('question.detail', question_id=question_id))
    elif request.method == 'GET':
        form.subject.data = question.subject
        form.content.data = question.content
    
    return render_template('question/question_form.html', form=form)

@bp.route('/delete/<int:question_id>/', methods=('POST',))
@login_required
def delete(question_id):
    question = Question.query.get_or_404(question_id)
    user = User.query.filter_by(username=session.get('username')).first()
    
    # 본인이 작성한 게시글이 아니면 접근 불가
    if question.user_id != user.id:
        abort(403)
    
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('question._list'))