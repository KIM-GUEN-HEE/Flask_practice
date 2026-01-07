from flask import Blueprint, render_template, request, url_for, session, flash, jsonify, current_app
from werkzeug.utils import redirect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
from sqlalchemy.exc import IntegrityError
import requests

from pybo import db, oauth
from pybo.models import User, UnverifiedUser, Question, Answer, QuestionLike, AnswerLike, QuestionBookmark, AnswerBookmark
import secrets
from pybo.login_required import login_required
from pybo.email_utils import send_verification_email

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login/', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        error = None
        
        if not username:
            error = '사용자ID를 입력해주세요.'
        elif not password:
            error = '비밀번호를 입력해주세요.'
        else:
            user = User.query.filter_by(username=username).first()
            if not user:
                error = '존재하지 않는 사용자입니다.'
            else:
                # If the user signed up via OAuth there may be no local password
                if not user.password:
                    error = '이 계정은 외부 로그인으로 생성되었습니다. 비밀번호로 로그인할 수 없습니다.'
                elif not check_password_hash(user.password, password):
                    error = '비밀번호가 올바르지 않습니다.'
                # If user has an email but hasn't verified it, prevent password login
                elif user.email and not user.email_verified:
                    error = '이메일 인증이 필요합니다. 등록하신 이메일을 확인해주세요.'
            
        if error is None:
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            flash('로그인이 완료되었습니다.')
            return redirect(url_for('main.index'))
        
        flash(error)
    
    return render_template('auth/login.html')


@bp.route('/logout/')
def logout():
    session.clear()
    flash('로그아웃되었습니다.')
    return redirect(url_for('main.index'))


@bp.route('/login/google')
def login_google():
    """Start Google OAuth login flow"""
    try:
        google = oauth.create_client('google')
        if not google:
            flash('Google OAuth가 설정되지 않았습니다. 환경변수(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)를 확인하세요.')
            return redirect(url_for('auth.login'))
        # localhost로 고정해서 redirect_uri 생성 (127.0.0.1 대신 localhost 사용)
        redirect_uri = url_for('auth.authorize_google', _external=True, _scheme='http').replace('127.0.0.1', 'localhost')
        print(f"[DEBUG] Redirect URI: {redirect_uri}")
        print(f"[DEBUG] Google Client: {google}")
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"[DEBUG] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Google 로그인 오류: {str(e)}')
        return redirect(url_for('auth.login'))


@bp.route('/authorize/google')
def authorize_google():
    """Handle callback from Google and sign in/create user"""
    google = oauth.create_client('google')
    try:
        token = google.authorize_access_token()
    except Exception as e:
        flash('구글 인증 중 오류가 발생했습니다.')
        return redirect(url_for('auth.login'))

    # ID Token (OpenID Connect) contains subject and email
    userinfo = None
    try:
        userinfo = google.parse_id_token(token)
    except Exception:
        # fallback to userinfo endpoint using access_token
        access_token = token.get('access_token') if isinstance(token, dict) else None
        if not access_token:
            flash('구글에서 사용자 정보를 가져올 수 없습니다 (access_token 누락).')
            return redirect(url_for('auth.login'))
        # Use Google's standard userinfo endpoint
        try:
            resp = requests.get(
                'https://openidconnect.googleapis.com/v1/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5,
            )
            resp.raise_for_status()
            userinfo = resp.json()
        except Exception as e:
            print(f"[DEBUG] userinfo fetch error: {e}")
            flash('구글 사용자 정보 조회 중 오류가 발생했습니다.')
            return redirect(url_for('auth.login'))

    email = userinfo.get('email')
    sub = userinfo.get('sub')

    if not email:
        flash('구글에서 이메일을 가져올 수 없습니다.')
        return redirect(url_for('auth.login'))

    # Try to find by provider id first
    user = None
    if sub:
        user = User.query.filter_by(oauth_provider='google', oauth_id=sub).first()

    # If not found, try matching by email
    if not user:
        user = User.query.filter(db.func.lower(User.email) == db.func.lower(email)).first()
        if user:
            # link account
            user.oauth_provider = 'google'
            user.oauth_id = sub
            db.session.commit()

    # Create new user if still not found
    if not user:
        base_username = email.split('@')[0]
        username_candidate = base_username
        i = 1
        while User.query.filter(db.func.lower(User.username) == db.func.lower(username_candidate)).first():
            username_candidate = f"{base_username}{i}"
            i += 1

        random_pw = generate_password_hash(secrets.token_urlsafe(16))
        user = User(username=username_candidate, password=random_pw, email=email,
                    oauth_provider='google', oauth_id=sub, create_date=datetime.utcnow())
        db.session.add(user)
        db.session.commit()

    # Log the user in
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    flash('구글 로그인이 완료되었습니다.')
    return redirect(url_for('main.index'))


@bp.route('/profile/')
@login_required
def profile():
    user = User.query.get(session.get('user_id'))
    if not user:
        flash('사용자를 찾을 수 없습니다.')
        return redirect(url_for('auth.login'))
    return render_template('auth/profile.html', user=user)


@bp.route('/liked/')
@login_required
def liked_items():
    user = User.query.get(session.get('user_id'))
    if not user:
        flash('사용자를 찾을 수 없습니다.')
        return redirect(url_for('auth.login'))

    liked_questions = Question.query.join(QuestionLike, Question.id == QuestionLike.question_id)\
        .filter(QuestionLike.user_id == user.id)\
        .order_by(QuestionLike.create_date.desc()).all()

    liked_answers = Answer.query.join(AnswerLike, Answer.id == AnswerLike.answer_id)\
        .filter(AnswerLike.user_id == user.id)\
        .order_by(AnswerLike.create_date.desc()).all()

    bookmarked_questions = Question.query.join(QuestionBookmark, Question.id == QuestionBookmark.question_id)\
        .filter(QuestionBookmark.user_id == user.id)\
        .order_by(QuestionBookmark.create_date.desc()).all()

    bookmarked_answers = Answer.query.join(AnswerBookmark, Answer.id == AnswerBookmark.answer_id)\
        .filter(AnswerBookmark.user_id == user.id)\
        .order_by(AnswerBookmark.create_date.desc()).all()

    return render_template('auth/liked.html', user=user, liked_questions=liked_questions, liked_answers=liked_answers,
                           bookmarked_questions=bookmarked_questions, bookmarked_answers=bookmarked_answers)


@bp.route('/bookmarks/')
@login_required
def bookmarked_items():
    user = User.query.get(session.get('user_id'))
    if not user:
        flash('사용자를 찾을 수 없습니다.')
        return redirect(url_for('auth.login'))

    bookmarked_questions = Question.query.join(QuestionBookmark, Question.id == QuestionBookmark.question_id)\
        .filter(QuestionBookmark.user_id == user.id)\
        .order_by(QuestionBookmark.create_date.desc()).all()

    bookmarked_answers = Answer.query.join(AnswerBookmark, Answer.id == AnswerBookmark.answer_id)\
        .filter(AnswerBookmark.user_id == user.id)\
        .order_by(AnswerBookmark.create_date.desc()).all()

    return render_template('auth/bookmarks.html', user=user, bookmarked_questions=bookmarked_questions, bookmarked_answers=bookmarked_answers)


@bp.route('/check_username/', methods=['POST'])
def check_username():
    """사용자ID 중복 확인 API"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'available': False, 'message': '사용자ID를 입력해주세요.'})
    
    if len(username) < 4:
        return jsonify({'available': False, 'message': '사용자ID는 4자 이상이어야 합니다.'})
    
    if not re.match(r'^[a-zA-Z0-9]+$', username):
        return jsonify({'available': False, 'message': '사용자ID는 영문과 숫자만 사용할 수 있습니다.'})
    
    # 중복 체크 (대소문자 구분 없이)
    # check existing confirmed users
    existing_user = User.query.filter(
        db.func.lower(User.username) == db.func.lower(username)
    ).first()
    # check pending unverified users to avoid duplicates
    pending = UnverifiedUser.query.filter(
        db.func.lower(UnverifiedUser.username) == db.func.lower(username)
    ).first()
    
    if existing_user or pending:
        return jsonify({'available': False, 'message': '이미 존재하는 사용자ID입니다.'})
    else:
        return jsonify({'available': True, 'message': '사용 가능한 사용자ID입니다.'})


@bp.route('/signup/', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        email = request.form.get('email', '').strip() if request.form.get('email') else None
        
        error = None
        
        # 디버깅: 입력값 확인
        print(f"Signup attempt - username: {username}, email: {email}")
        
        # 입력 검증
        if not username:
            error = '사용자ID를 입력해주세요.'
        elif len(username) < 4:
            error = '사용자ID는 4자 이상이어야 합니다.'
        elif not re.match(r'^[a-zA-Z0-9]+$', username):
            error = '사용자ID는 영문과 숫자만 사용할 수 있습니다.'
        elif not password:
            error = '비밀번호를 입력해주세요.'
        elif len(password) < 8:
            error = '비밀번호는 8자 이상이어야 합니다.'
        elif password != password2:
            error = '비밀번호가 일치하지 않습니다.'
        
        # 중복 체크 (대소문자 구분 없이)
        if error is None:
            # 기존 사용자명을 대소문자 구분 없이 확인
            existing_user = User.query.filter(
                db.func.lower(User.username) == db.func.lower(username)
            ).first()
            if existing_user:
                error = '이미 존재하는 사용자ID입니다.'
            elif email:
                # 이메일도 대소문자 구분 없이 확인
                existing_email = User.query.filter(
                    db.func.lower(User.email) == db.func.lower(email)
                ).first()
                if existing_email:
                    error = '이미 등록된 이메일입니다.'
        
        # 이메일이 주어진 경우, 바로 User로 저장하지 않고 임시 테이블에 저장한 뒤 인증 완료 시 생성
        if error is None:
            try:
                if email:
                    # create or update pending unverified entry
                    token = secrets.token_urlsafe(48)
                    # If there's already a pending entry for this email, update it instead
                    existing_pending = UnverifiedUser.query.filter(
                        db.func.lower(UnverifiedUser.email) == db.func.lower(email)
                    ).first()
                    if existing_pending:
                        existing_pending.username = username
                        existing_pending.password = generate_password_hash(password)
                        existing_pending.token = token
                        existing_pending.create_date = datetime.utcnow()
                        db.session.commit()
                        pending = existing_pending
                    else:
                        pending = UnverifiedUser(
                            username=username,
                            password=generate_password_hash(password),
                            email=email,
                            token=token,
                            create_date=datetime.utcnow()
                        )
                        db.session.add(pending)
                        db.session.commit()

                    verify_url = url_for('auth.verify', token=token, _external=True)
                    sent = send_verification_email(email, verify_url)
                    return render_template('auth/verify_sent.html', email=email, sent=sent, verify_link=verify_url)
                else:
                    # no email provided -> create user immediately
                    user = User(
                        username=username,
                        password=generate_password_hash(password),
                        email=None,
                        create_date=datetime.utcnow()
                    )
                    db.session.add(user)
                    db.session.commit()
                    flash('회원가입이 완료되었습니다.')
                    return redirect(url_for('auth.login'))
            except IntegrityError as e:
                db.session.rollback()
                # 데이터베이스 제약조건 위반 시 (동시성 이슈 등)
                if User.query.filter(
                    db.func.lower(User.username) == db.func.lower(username)
                ).first():
                    error = '이미 존재하는 사용자ID입니다.'
                elif email and User.query.filter(
                    db.func.lower(User.email) == db.func.lower(email)
                ).first():
                    error = '이미 등록된 이메일입니다.'
                else:
                    error = f'데이터베이스 제약조건 위반: {str(e)}'
            except Exception as e:
                db.session.rollback()
                import traceback
                error = f'회원가입 중 오류가 발생했습니다: {str(e)}'
                print(f"Signup error: {traceback.format_exc()}")  # 디버깅용
        
        # 에러가 있을 때만 flash
        if error:
            flash(error)
    
    return render_template('auth/signup.html')



@bp.route('/verify/<token>')
def verify(token):
    # Find pending registration by token
    pending = UnverifiedUser.query.filter_by(token=token).first()
    if not pending:
        flash('유효하지 않거나 만료된 인증 링크입니다.')
        return redirect(url_for('auth.login'))

    # Optionally enforce token age (e.g., 24h)
    age_seconds = (datetime.utcnow() - pending.create_date).total_seconds()
    if age_seconds > 86400:
        # expired
        db.session.delete(pending)
        db.session.commit()
        flash('인증 링크가 만료되었습니다. 다시 회원가입 해주세요.')
        return render_template('auth/verify_result.html', success=False)

    # Create the confirmed user
    try:
        user = User(
            username=pending.username,
            password=pending.password,
            email=pending.email,
            create_date=datetime.utcnow(),
            email_verified=True,
            verified_at=datetime.utcnow()
        )
        db.session.add(user)
        # remove pending
        db.session.delete(pending)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('사용자 생성 중 오류가 발생했습니다. 관리자에게 문의하세요.')
        return render_template('auth/verify_result.html', success=False)

    flash('이메일 인증이 완료되었습니다. 로그인해주세요.')
    return render_template('auth/verify_result.html', success=True)

