from datetime import datetime, timedelta
from sqlalchemy import func

from flask import Blueprint, render_template, request, url_for, session, abort, jsonify, g
from werkzeug.utils import redirect
from .. import db

from pybo.models import Question, User, QuestionLike, QuestionBookmark, Answer, AnswerLike, QuestionView

from pybo.forms import QuestionForm, AnswerForm
from pybo.login_required import login_required

bp = Blueprint('question', __name__, url_prefix='/question')

@bp.route('/list/')
@login_required
def _list():
    page = request.args.get('page', type=int, default=1)
    per_page = request.args.get('per_page', type=int, default=10)
    sort = request.args.get('sort', 'recent', type=str)
    keyword = request.args.get('keyword', '', type=str).strip()
    
    if per_page not in (10, 30, 50, 100):
        per_page = 10
    
    # Start with base query
    base_query = Question.query
    
    # Apply search filter if keyword is provided
    if keyword:
        # 검색 키워드에서 공백 제거
        keyword_no_space = keyword.replace(' ', '')
        base_query = base_query.filter(
            (func.replace(Question.subject, ' ', '').ilike(f'%{keyword_no_space}%')) | 
            (func.replace(Question.content, ' ', '').ilike(f'%{keyword_no_space}%'))
        )
    
    # Determine sorting order
    if sort == 'likes_desc':
        # Order by number of likes (descending)
        question_list = db.session.query(Question).filter(
            base_query.whereclause if hasattr(base_query, 'whereclause') else True
        ).outerjoin(
            QuestionLike, Question.id == QuestionLike.question_id
        ).group_by(Question.id).order_by(
            func.count(QuestionLike.id).desc(), Question.create_date.desc()
        ).paginate(page=page, per_page=per_page)
    elif sort == 'likes_asc':
        # Order by number of likes (ascending)
        question_list = db.session.query(Question).filter(
            base_query.whereclause if hasattr(base_query, 'whereclause') else True
        ).outerjoin(
            QuestionLike, Question.id == QuestionLike.question_id
        ).group_by(Question.id).order_by(
            func.count(QuestionLike.id).asc(), Question.create_date.desc()
        ).paginate(page=page, per_page=per_page)
    elif sort == 'bookmarks_desc':
        # Order by number of bookmarks (descending)
        question_list = db.session.query(Question).filter(
            base_query.whereclause if hasattr(base_query, 'whereclause') else True
        ).outerjoin(
            QuestionBookmark, Question.id == QuestionBookmark.question_id
        ).group_by(Question.id).order_by(
            func.count(QuestionBookmark.id).desc(), Question.create_date.desc()
        ).paginate(page=page, per_page=per_page)
    elif sort == 'bookmarks_asc':
        # Order by number of bookmarks (ascending)
        question_list = db.session.query(Question).filter(
            base_query.whereclause if hasattr(base_query, 'whereclause') else True
        ).outerjoin(
            QuestionBookmark, Question.id == QuestionBookmark.question_id
        ).group_by(Question.id).order_by(
            func.count(QuestionBookmark.id).asc(), Question.create_date.desc()
        ).paginate(page=page, per_page=per_page)
    elif sort == 'views_desc':
        # Order by view count (descending)
        question_list = base_query.order_by(Question.view_count.desc(), Question.create_date.desc()).paginate(page=page, per_page=per_page)
    elif sort == 'views_asc':
        # Order by view count (ascending)
        question_list = base_query.order_by(Question.view_count.asc(), Question.create_date.desc()).paginate(page=page, per_page=per_page)
    elif sort == 'oldest':
        # Order by oldest (create_date ascending)
        question_list = base_query.order_by(Question.create_date.asc()).paginate(page=page, per_page=per_page)
    else:
        # Default: Order by recent (create_date descending)
        question_list = base_query.order_by(Question.create_date.desc()).paginate(page=page, per_page=per_page)
    
    # Calculate pagination range
    pages_to_show = []
    if question_list.pages <= 10:
        pages_to_show = list(range(1, question_list.pages + 1))
    else:
        start_page = max(1, question_list.page - 4)
        end_page = min(question_list.pages, start_page + 9)
        if end_page - start_page < 9:
            start_page = max(1, end_page - 9)
        
        if start_page > 1:
            pages_to_show.append(1)
            if start_page > 2:
                pages_to_show.append('...')
        
        pages_to_show.extend(range(start_page, end_page + 1))
        
        if end_page < question_list.pages:
            if end_page < question_list.pages - 1:
                pages_to_show.append('...')
            pages_to_show.append(question_list.pages)
    
    return render_template('question/question_list.html', question_list=question_list, current_sort=sort, pages_to_show=pages_to_show, keyword=keyword)


@bp.route('/detail/<int:question_id>/')
@login_required
def detail(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)
    
    # 조회수 처리 - 1시간 내 동일 사용자 중복 조회 방지
    if g.user:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_view = QuestionView.query.filter_by(
            question_id=question_id,
            user_id=g.user.id
        ).filter(QuestionView.created_at > one_hour_ago).first()
        
        # 1시간 내 기록이 없으면 조회수 증가 및 기록 추가
        if not recent_view:
            question.view_count += 1
            view_record = QuestionView(
                question_id=question_id,
                user_id=g.user.id,
                created_at=datetime.utcnow()
            )
            db.session.add(view_record)
            db.session.commit()
    
    # Get answer sort parameter
    answer_sort = request.args.get('answer_sort', 'recent', type=str)
    
    # Sort answers based on parameter
    if answer_sort == 'likes_desc':
        # Order by number of likes (descending)
        answers = db.session.query(Answer).filter(
            Answer.question_id == question_id
        ).outerjoin(
            AnswerLike, Answer.id == AnswerLike.answer_id
        ).group_by(Answer.id).order_by(
            func.count(AnswerLike.id).desc(), Answer.create_date.desc()
        ).all()
    elif answer_sort == 'likes_asc':
        # Order by number of likes (ascending)
        answers = db.session.query(Answer).filter(
            Answer.question_id == question_id
        ).outerjoin(
            AnswerLike, Answer.id == AnswerLike.answer_id
        ).group_by(Answer.id).order_by(
            func.count(AnswerLike.id).asc(), Answer.create_date.desc()
        ).all()
    else:
        # Default: Order by recent (create_date descending)
        answers = Answer.query.filter_by(question_id=question_id).order_by(Answer.create_date.desc()).all()
    
    question.answer_set = answers
    
    return render_template('question/question_detail.html', question=question, form=form, answer_sort=answer_sort)

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


@bp.route('/like/<int:question_id>/', methods=('POST',))
@login_required
def like_question(question_id):
    question = Question.query.get_or_404(question_id)
    user = User.query.filter_by(username=session.get('username')).first()
    
    # 이미 좋아요를 눌렀으면 취소
    existing_like = QuestionLike.query.filter_by(
        question_id=question_id, user_id=user.id
    ).first()
    
    if existing_like:
        db.session.delete(existing_like)
    else:
        like = QuestionLike(question_id=question_id, user_id=user.id, create_date=datetime.now())
        db.session.add(like)
    
    db.session.commit()
    
    like_count = QuestionLike.query.filter_by(question_id=question_id).count()
    is_liked = QuestionLike.query.filter_by(
        question_id=question_id, user_id=user.id
    ).first() is not None
    
    return jsonify({
        'success': True,
        'like_count': like_count,
        'is_liked': is_liked
    })


@bp.route('/bookmark/<int:question_id>/', methods=('POST',))
@login_required
def bookmark_question(question_id):
    question = Question.query.get_or_404(question_id)
    user = User.query.filter_by(username=session.get('username')).first()
    
    # 이미 즐겨찾기를 했으면 취소
    existing_bookmark = QuestionBookmark.query.filter_by(
        question_id=question_id, user_id=user.id
    ).first()
    
    if existing_bookmark:
        db.session.delete(existing_bookmark)
    else:
        bookmark = QuestionBookmark(question_id=question_id, user_id=user.id, create_date=datetime.now())
        db.session.add(bookmark)
    
    db.session.commit()
    
    bookmark_count = QuestionBookmark.query.filter_by(question_id=question_id).count()
    is_bookmarked = QuestionBookmark.query.filter_by(
        question_id=question_id, user_id=user.id
    ).first() is not None
    
    return jsonify({
        'success': True,
        'bookmark_count': bookmark_count,
        'is_bookmarked': is_bookmarked
    })