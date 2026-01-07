from datetime import datetime
from pybo import db

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text(), nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', backref=db.backref('question_set'))


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'))
    question = db.relationship('Question', backref=db.backref('answer_set'))
    content = db.Column(db.Text(), nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', backref=db.backref('answer_set'))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    # For OAuth-only users password can be empty -> allow nullable
    password = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    # OAuth provider info (e.g. 'google') and provider user id
    oauth_provider = db.Column(db.String(50), nullable=True)
    oauth_id = db.Column(db.String(200), nullable=True)
    create_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    # Email verification
    email_verified = db.Column(db.Boolean(), nullable=False, default=False)
    verified_at = db.Column(db.DateTime(), nullable=True)


class UnverifiedUser(db.Model):
    __tablename__ = 'unverified_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    # store hashed password until verification
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    token = db.Column(db.String(300), unique=True, nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)


class QuestionLike(db.Model):
    __tablename__ = 'question_like'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    question = db.relationship('Question', backref=db.backref('like_set'))
    user = db.relationship('User', backref=db.backref('question_like_set'))
    __table_args__ = (db.UniqueConstraint('question_id', 'user_id', name='question_like_unique'),)


class QuestionBookmark(db.Model):
    __tablename__ = 'question_bookmark'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    question = db.relationship('Question', backref=db.backref('bookmark_set'))
    user = db.relationship('User', backref=db.backref('question_bookmark_set'))
    __table_args__ = (db.UniqueConstraint('question_id', 'user_id', name='question_bookmark_unique'),)


class AnswerLike(db.Model):
    __tablename__ = 'answer_like'
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    answer = db.relationship('Answer', backref=db.backref('like_set'))
    user = db.relationship('User', backref=db.backref('answer_like_set'))
    __table_args__ = (db.UniqueConstraint('answer_id', 'user_id', name='answer_like_unique'),)


class AnswerBookmark(db.Model):
    __tablename__ = 'answer_bookmark'
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    create_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    answer = db.relationship('Answer', backref=db.backref('bookmark_set'))
    user = db.relationship('User', backref=db.backref('answer_bookmark_set'))
    __table_args__ = (db.UniqueConstraint('answer_id', 'user_id', name='answer_bookmark_unique'),)
    