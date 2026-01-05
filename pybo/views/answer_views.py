from datetime import datetime

from flask import Blueprint, url_for, request, render_template, session, abort
from werkzeug.utils import redirect

from pybo import db
from ..forms import AnswerForm
from pybo.models import Question, Answer, User
from pybo.login_required import login_required

bp = Blueprint('answer',__name__, url_prefix='/answer')

@bp.route('/create/<int:question_id>', methods=('POST',))
@login_required
def create(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)
    if form.validate_on_submit():
        user = User.query.filter_by(username=session.get('username')).first()
        content = request.form['content']
        answer = Answer(content=content, create_date=datetime.now(), user_id=user.id)
        question.answer_set.append(answer)
        db.session.commit()
        return redirect(url_for('question.detail', question_id=question_id))
    return render_template('question/question_detail.html', question=question, form=form)

@bp.route('/modify/<int:answer_id>/', methods=('GET', 'POST'))
@login_required
def modify(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    user = User.query.filter_by(username=session.get('username')).first()
    
    # 본인이 작성한 답변이 아니면 접근 불가
    if answer.user_id != user.id:
        abort(403)
    
    form = AnswerForm()
    if request.method == 'POST' and form.validate_on_submit():
        form.populate_obj(answer)
        answer.create_date = datetime.now()
        db.session.commit()
        return redirect(url_for('question.detail', question_id=answer.question_id))
    elif request.method == 'GET':
        form.content.data = answer.content
    
    return render_template('question/question_detail.html', question=answer.question, form=form)

@bp.route('/delete/<int:answer_id>/', methods=('POST',))
@login_required
def delete(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    user = User.query.filter_by(username=session.get('username')).first()
    
    # 본인이 작성한 답변이 아니면 접근 불가
    if answer.user_id != user.id:
        abort(403)
    
    question_id = answer.question_id
    db.session.delete(answer)
    db.session.commit()
    return redirect(url_for('question.detail', question_id=question_id))