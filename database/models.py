from flask_config import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100), nullable=False)
    user_password = db.Column(db.String(200), default=None)
    user_type = db.Column(db.String(1), nullable=False)
    datetime_added = db.Column(db.DateTime, nullable=False)


class UserToken(db.Model):
    __tablename__ = 'user_tokens'

    token_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_token = db.Column(db.String(100), nullable=False)
    device_id = db.Column(db.String(200), nullable=False)


class UserData(db.Model):
    __tablename__ = 'users_data'

    user_id = db.Column(db.Integer, primary_key=True)
    user_public_id = db.Column(db.String(36), nullable=False)
    user_name = db.Column(db.String(25), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    avatar_link = db.Column(db.String(100))
    current_level = db.Column(db.Integer, default=1)
    current_level_XP = db.Column(db.Integer, default=0)
    streak_days = db.Column(db.Integer, default=0)
    subscribed = db.Column(db.Boolean, default=0)
    streak_datetime = db.Column(db.DateTime, default=datetime(1900, 1, 1))
    completed_parts = db.Column(db.JSON, default=[0, 0, 0, 0])
    notifications_are_checked = db.Column(db.Boolean, default=1)


class UserStatistics(db.Model):
    __tablename__ = 'users_statistics'

    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    obtained_XP = db.Column(db.Integer)
    obtained_time = db.Column(db.Integer)
    obtained_exercises = db.Column(db.Integer)
    obtained_trainings = db.Column(db.Integer)
    obtained_achievements = db.Column(db.Integer)


class PrivacySettings(db.Model):
    __tablename__ = 'privacy_settings'

    user_id = db.Column(db.Integer, primary_key=True)
    duels_invites_from = db.Column(db.String(1), nullable=False, default='f')
    show_in_ratings = db.Column(db.Boolean, nullable=False, default=True)
    profile_visible = db.Column(db.Boolean, nullable=False, default=True)


class PrivacyDuelsException(db.Model):
    __tablename__ = 'privacy_duels_exceptions'

    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    exception_id = db.Column(db.Integer, nullable=False)


class Friendship(db.Model):
    __tablename__ = 'friendships'

    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    friend_id = db.Column(db.Integer, nullable=False)
    datetime_added = db.Column(db.DateTime, nullable=False)


class FriendshipRequest(db.Model):
    __tablename__ = 'friendship_requests'

    request_id = db.Column(db.Integer, primary_key=True)
    requesting_id = db.Column(db.Integer, nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)


class Notification(db.Model):
    __tablename__ = 'notifications'

    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    id_user_from = db.Column(db.Integer, nullable=False)
    notification_type = db.Column(db.String(1), nullable=False)
    datetime_sent = db.Column(db.DateTime, nullable=False)


class FirebaseToken(db.Model):
    __tablename__ = 'firebase_tokens'

    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    token = db.Column(db.String(200), nullable=False)
    device_id = db.Column(db.String(200), nullable=False)


class ExerciseReport(db.Model):
    EXERCISE_MISTAKE = 1
    CANT_UNDERSTAND = 2
    ANSWER_IS_CORRECT = 3
    ANSWER_IS_INCORRECT = 4

    __tablename__ = 'exercises_reports'

    record_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    exercise_number = db.Column(db.Integer, nullable=False)
    bug_type = db.Column(db.Integer, nullable=False)


def as_dict(model):
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}


def as_array(model):
    return [getattr(model, c.name) for c in model.__table__.columns]


def as_dict_array(models):
    return [{c.name: getattr(model, c.name) for c in model.__table__.columns} for model in models]



