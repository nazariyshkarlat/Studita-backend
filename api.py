from flask import jsonify, request, Response
import bcrypt
import firebase_admin
import firebase_admin.messaging as messaging
from firebase_admin import credentials
import re
from user.achievements import achievements_utils
from user import statistics_utils
from user.achievements.achievements_info import achievements
import os
import string
import random
from sqlalchemy import func
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as r
from flask_config import app
import copy
from user import level_utils
from user import user_utils
from database.models import *
from sympy.solvers import solve
from sympy import Symbol
import json as j
from flask_cors import CORS
import uuid
import os.path

SCOPES = ['https://www.googleapis.com/auth/userinfo.profile']

utf = 'UTF-8'
CLIENT_ID = "568009941526-4te9dh9l7vnfo22bmi9hfdk9q5ae3eqp.apps.googleusercontent.com"
API_KEY = 'AIzaSyA1PtDc0aFfmlJ3iRZVQhj9270Tfb0PVrQ'

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

cred = credentials.Certificate("serviceAccountKey.json")
default_app = firebase_admin.initialize_app(cred)

with open('dict/levels_dict', 'r', encoding='utf-8') as f:
    levels = f.read()
    levels = j.loads(levels)

with open('dict/chapters_dict', 'r', encoding='utf-8') as f:
    chapters = f.read()
    chapters = j.loads(chapters)


@app.route('/levels', methods=['GET'])
def get_levels():
    return json_200(levels)


@app.route('/levels/<number>', methods=['GET'])
def get_level(number):
    return number_bounds(number, levels)


@app.route('/chapters', methods=['GET'])
def get_chapters():
    return json_200(chapters)


@app.route('/chapters/<number>', methods=['GET'])
def get_chapter(number):
    return number_bounds(number, chapters)


@app.route('/user_data', methods=['GET'])
def get_user_data():
    try:
        user_id = request.args.get("user_id")
        today = convert_datetime_str(request.headers['Date']).date()
        user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
        if (today - timedelta(days=1)) > user_data.streak_datetime.date():
            user_data.streak_days = 0
        response = as_dict(user_data)
        db.session.commit()
        response.update(
            {"today_completed_exercises": level_utils.get_today_completed_exercises_count(today, user_data, db)})
        return json_200(response)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/complete_exercises', methods=['POST'])
def complete_exercises():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):

            completed_datetime = convert_datetime_str(json['completed_exercises_data']['datetime'])

            if db.session.query(UserStatistics).filter_by(user_id=user_id,
                                                          datetime=completed_datetime).scalar() is not None:
                return Response(status=200)

            user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
            percent = json['completed_exercises_data']['percent']
            chapter_number = json['completed_exercises_data']['chapter_number']
            chapter_part_in_chapter_number = json['completed_exercises_data']['chapter_part_in_chapter_number']
            obtained_time = json['completed_exercises_data']['obtained_time']
            exercises_bonus_correct_count = json['completed_exercises_data']['exercises_bonus_correct_count']

            is_training = user_data.completed_parts[chapter_number - 1] >= chapter_part_in_chapter_number

            obtained_XP = level_utils.get_obtained_XP(user_data, percent, is_training, db, completed_datetime.date(),
                                                      exercises_bonus_correct_count)

            new_levels_count = level_utils.get_new_levels_count(user_data, obtained_XP)
            new_level_XP = level_utils.get_new_level_XP(user_data, obtained_XP)

            user_stat = UserStatistics(user_id=user_id)

            user_stat.datetime = completed_datetime

            if is_training:
                user_stat.completed_trainings = 1
            else:
                user_stat.completed_exercises = 1

            user_stat.obtained_XP = obtained_XP
            user_stat.obtained_time = obtained_time

            db.session.add(user_stat)

            if not is_training:
                new_completed_parts = user_data.completed_parts.copy()
                if new_completed_parts[chapter_number - 1] + 1 == chapter_part_in_chapter_number:
                    new_completed_parts[chapter_number - 1] += 1
                    user_data.completed_parts = new_completed_parts

                    for chapter in chapters:
                        if chapter["chapter_number"] == chapter_number and len(chapter["parts"]) == new_completed_parts[chapter_number - 1]:
                            user_stat.completed_chapters = 1

            user_data.current_level = UserData.current_level + new_levels_count
            user_data.current_level_XP = new_level_XP

            if (completed_datetime.date() - timedelta(days=1)) >= user_data.streak_datetime.date():
                if (completed_datetime.date() - timedelta(days=1)) > user_data.streak_datetime.date():
                    user_data.streak_days = 1
                else:
                    user_data.streak_days = UserData.streak_days + 1

                user_data.streak_datetime = completed_datetime

            user_stat.days_streak = user_data.streak_days

            achievements_utils.giveNewImprovableAchievements(user_id, db)

            try:
                db.session.commit()
            except Exception as e:
                print(e)
            return Response(status=200)
        else:
            return Response(status=400)

    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    try:
        json = j.loads(request.form.to_dict()['json'])
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
            if user_utils.user_name_not_exists(db, json['user_data']['user_name'], user_data.user_name):
                user_name = json['user_data']['user_name'].strip()

                name = json['user_data'].get('name', None)

                bio = json['user_data'].get('bio', None)

                if name:
                    name = name.strip()
                    if len(name) == 0:
                        name = None

                if bio:
                    bio = bio.strip()
                    if len(bio) == 0:
                        bio = None

                if user_utils.is_valid_profile_data(user_name, name, bio):
                    if 'avatar' in request.files:
                        file_name = uuid.uuid1().hex
                        file_name = '{0}.jpg'.format(file_name)
                        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                        if user_data.avatar_link:
                            try:
                                os.remove("{0}/{1}".format(app.config['UPLOAD_FOLDER'],
                                                           user_data.avatar_link.split("avatars/")[1]))
                            except Exception as e:
                                print(e)
                        request.files['avatar'].save(full_filename)
                        if user_data.avatar_link is None:
                            achievements_utils.giveNonImprovableAchievementByType(achievements_utils.TYPE_SET_AVATAR, user_id, db)

                        user_data.avatar_link = "http://37.53.93.223:34867/static/avatars/{0}".format(file_name)
                    else:
                        user_data.avatar_link = json['user_data'].get('avatar_link', None)
                    user_data.user_name = user_name

                    if user_data.name is None and name is not None:
                        achievements_utils.giveNonImprovableAchievementByType(achievements_utils.TYPE_SET_NAME, user_id, db)
                    if user_data.bio is None and bio is not None:
                        achievements_utils.giveNonImprovableAchievementByType(achievements_utils.TYPE_SET_BIO, user_id, db)

                    user_data.name = name
                    user_data.bio = bio
                    db.session.commit()
                    return json_200({"avatar_link": user_data.avatar_link})
                else:
                    return Response(status=400)
            else:
                return Response(status=409)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/is_user_name_available', methods=['GET'])
def is_user_name_available():
    try:
        user_name = request.args.get('user_name').strip()
        if user_utils.match_user_name(user_name):
            return Response(
                str(not db.session.query(UserData).filter_by(user_name=user_name).scalar()).lower(),
                status=200)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/user_statistics/<time>', methods=['GET'])
def get_user_statistics_by_time(time):
    try:
        user_id = request.args.get("user_id")

        today = convert_datetime_str(request.headers['Date']).date()
        yesterday = today - timedelta(days=1)
        week = today - timedelta(days=7)
        month = today - timedelta(days=30)

        today_filter = func.DATE(UserStatistics.datetime) == today
        yesterday_filter = func.DATE(UserStatistics.datetime) == yesterday
        week_filter = func.DATE(UserStatistics.datetime) >= week
        month_filter = func.DATE(UserStatistics.datetime) >= month

        query = db.session.query(db.func.coalesce(db.func.sum(UserStatistics.obtained_XP), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.time_spent), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.completed_exercises), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.completed_trainings), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_achievements), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.completed_chapters), 0),
                                 db.func.coalesce(db.func.max(UserStatistics.days_streak), 0)) \
                .filter_by(user_id=user_id)

        if time == "month":
            results = query.filter(month_filter)[0]
        elif time == "week":
            results = query.filter(week_filter)[0]
        elif time == "yesterday":
            results = query.filter(yesterday_filter)[0]
        elif time == "today":
            results = query.filter(today_filter)[0]
        else:
            return Response(status=404)

        if results:
            int_results = (int(result) for result in results)
            results_dict = dict(zip(statistics_utils.labels, int_results))
            results_dict.update({"time_type": time})
            return json_200(results_dict)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/user_statistics', methods=['GET'])
def get_user_statistics():
    try:
        user_id = request.args.get("user_id")
        times = ["today", "yesterday", "week", "month"]

        today = convert_datetime_str(request.headers['Date']).date()
        yesterday = today - timedelta(days=1)
        week = today - timedelta(days=7)
        month = today - timedelta(days=30)

        today_filter = func.DATE(UserStatistics.datetime) == today
        yesterday_filter = func.DATE(UserStatistics.datetime) == yesterday
        week_filter = func.DATE(UserStatistics.datetime) >= week
        month_filter = func.DATE(UserStatistics.datetime) >= month

        query = db.session.query(db.func.coalesce(db.func.sum(UserStatistics.obtained_XP), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.time_spent), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.completed_exercises), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.completed_trainings), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_achievements), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.completed_chapters), 0),
                                 db.func.coalesce(db.func.max(UserStatistics.days_streak), 0)) \
            .filter_by(user_id=user_id)

        results_array = [query.filter(today_filter)[0], query.filter(yesterday_filter)[0], query.filter(week_filter)[0],
                         query.filter(month_filter)[0]]

        results_dict_array = []
        if results_array:
            for idx, results in enumerate(results_array):
                int_results = (int(result) for result in results)
                results_dict = dict(zip(statistics_utils.labels, int_results))
                results_dict.update({'time_type': times[idx]})
                results_dict_array.append(results_dict)
            return json_200(results_dict_array)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/sign_in_with_google', methods=['POST'])
def sign_in_with_google():
    try:
        json = request.get_json()
        idToken = json['id_token']
        idInfo = id_token.verify_oauth2_token(idToken, requests.Request(), CLIENT_ID)
        if idInfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return Response(status=400)
        else:
            user_email = idInfo["email"]
            user = db.session.query(User).filter_by(user_email=user_email, user_type='g').first()

            if not user:
                profile_json = r.get('https://people.googleapis.com/v1/people/' + idInfo[
                    'sub'] + '?key=' + API_KEY + '&personFields=photos').json()
                is_default_photo = any([photo.get('default') for photo in profile_json['photos']])
                user_data = create_new_user(user_email, None, json, None if is_default_photo else idInfo["picture"])
            else:
                user_data = db.session.query(UserData).filter_by(user_id=user.user_id).one()

            if user_data:
                token = create_token(user_data.user_id, json['push_data']['device_id'])
                create_firebase_token(user_data.user_id, json)

                db.session.commit()

                if not user:
                    achievements_utils.giveNewImprovableAchievements(user_data.user_id, db)

                return json_200(
                    {**{'user_id': user_data.user_id, 'user_token': token, 'is_after_sign_up': not user},
                     "user_data": {**as_dict(user_data)}})
            else:
                return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/sign_up', methods=['POST'])
def sign_up():
    try:
        json = request.get_json()
        user_email = json['user_email']
        user_password = json['user_password']
        if (len(user_password) < 6) or (not EMAIL_REGEX.match(user_email)):
            return Response(status=400)
        user = db.session.query(User).filter_by(user_email=user_email, user_type='s').first()
        if not user:
            if new_user := create_new_user(user_email, user_password, json, None):
                achievements_utils.giveNewImprovableAchievements(new_user.user_id, db, False, True)
                return Response(status=200)
            else:
                return Response(status=400)
        else:
            return Response(status=409)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/log_in', methods=['POST'])
def log_in():
    try:
        json = request.get_json()
        user_email = json['user_email']
        user_password = json['user_password']
        if (len(user_password) < 6) or (not EMAIL_REGEX.match(user_email)):
            raise Exception()
        user = db.session.query(User).filter_by(user_email=user_email, user_type='s').first()
        if user:
            if check_bcrypt(user_password, user.user_password):

                user_data = db.session.query(UserData).filter_by(user_id=user.user_id).one()

                token = create_token(user.user_id, json['push_data']['device_id'])
                create_firebase_token(user.user_id, json)

                db.session.commit()

                if json['is_first_log_in'] is True:
                    achievements_utils.giveNewImprovableAchievements(user_data.user_id, db, True, False)
                return json_200(
                    {**{'user_id': user.user_id, 'user_token': token}, "user_data": {**as_dict(user_data)}})
            else:
                return Response(status=400)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/sign_out', methods=['POST'])
def sign_out():
    json = request.get_json()

    tokens = db.session.query(UserToken) \
        .filter(UserToken.device_id == json['device_id']) \
        .all()

    firebase_tokens = db.session.query(FirebaseToken) \
        .filter(FirebaseToken.device_id == json['device_id']) \
        .all()

    for firebase_token in firebase_tokens:
        db.session.delete(firebase_token)

    for token in tokens:
        db.session.delete(token)

    db.session.commit()
    if len(firebase_tokens) != 0 and len(tokens) != 0:
        return Response(status=200)
    else:
        return Response(status=400)


@app.route('/subscribe_email', methods=['POST'])
def subscribe_email():
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']
        if check_token(user_id, token):
            user = db.session.query(User).filter_by(user_id=user_id).one()
            user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
            user_data.subscribed = True
            db.session.commit()
            return json_200({"user_email": user.user_email})
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/unsubscribe_email', methods=['POST'])
def unsubscribe_email():
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']
        if check_token(user_id, token):
            user = db.session.query(User).filter_by(user_id=user_id).one()
            user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
            user_data.subscribed = False
            db.session.commit()
            return json_200({"user_email": user.user_email})
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/privacy_settings', methods=['POST'])
def get_privacy_settings():
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']
        if check_token(user_id, token):
            privacy_settings = db.session.query(PrivacySettings).filter_by(user_id=user_id).one()
            duels_exceptions = db.session.query(PrivacyDuelsException.exception_id).filter_by(user_id=user_id).all()

            exceptions_names = db.session.query(UserData.user_name).filter(UserData.user_id.in_(duels_exceptions)).all()
            exceptions_names = [name for name, *_ in exceptions_names]

            if len(exceptions_names) == 0 and privacy_settings.duels_invites_from == 'e':
                privacy_settings.duels_invites_from = 'n'

            db.session.commit()

            return json_200({"duels_invites_from": privacy_settings.duels_invites_from,
                             "show_in_ratings": privacy_settings.show_in_ratings,
                             "profile_is_visible": privacy_settings.profile_is_visible,
                             "duels_exceptions": exceptions_names})
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/privacy_duels_exceptions', methods=['POST'])
def get_privacy_duels_exceptions_list():
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']

        per_page = int(request.args.get("per_page"))
        page_number = int(request.args.get("page_number"))
        if check_token(user_id, token):

            items = db.session.query(UserData.user_id, UserData.user_name, UserData.avatar_link,
                                     PrivacyDuelsException.exception_id) \
                .group_by(Friendship.user_id, Friendship.friend_id) \
                .outerjoin(Friendship,
                           db.or_(Friendship.user_id == UserData.user_id, Friendship.friend_id == UserData.user_id)) \
                .outerjoin(PrivacyDuelsException, PrivacyDuelsException.exception_id == UserData.user_id) \
                .filter(db.or_(Friendship.user_id == user_id, Friendship.friend_id == user_id)) \
                .filter(UserData.user_id != user_id) \
                .order_by(PrivacyDuelsException.exception_id == None, UserData.user_name.asc()) \
                .paginate(page_number, per_page, False).items

            if len(items) == 0:
                return json_200([])

            friends = [dict(zip(["user_id", "user_name", "avatar_link", "is_exception"], friend)) for friend in
                       items]

            for friend in friends:
                friend.update({'is_exception': friend["is_exception"] is not None})

            return json_200(friends)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/notifications', methods=['POST'])
def get_notifications():
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']

        per_page = int(request.args.get("per_page"))
        page_number = int(request.args.get("page_number"))
        if check_token(user_id, token):

            if page_number == 1:
                db.session.query(UserData).filter_by(user_id=user_id).update(dict(notifications_are_checked=True))
                db.session.commit()

            notifications = db.session.query(UserData.user_id,
                                             UserData.user_name,
                                             UserData.avatar_link,
                                             Notification.id_user_from,
                                             Notification.notification_type,
                                             Notification.datetime_sent) \
                .join(UserData, Notification.id_user_from == UserData.user_id, isouter=True) \
                .filter(db.or_(UserData.user_id == Notification.id_user_from, Notification.id_user_from == None)) \
                .filter(Notification.user_id == user_id).order_by(db.desc(Notification.datetime_sent)).paginate(
                page_number, per_page, False).items

            notifications_dicts = []
            for notification in notifications:
                notification = dict(zip(["user_id", "user_name", "avatar_link", "id_user_from", "notification_type", "datetime_sent"], notification))
                time_diff = datetime.utcnow() - notification["datetime_sent"]
                del notification["datetime_sent"]
                if notification["id_user_from"] is not None:
                    is_my_friend = db.session.query(Friendship).filter(
                        db.or_(db.and_(Friendship.user_id == int(user_id),
                                       Friendship.friend_id == notification['user_id']),
                               db.and_(Friendship.user_id == notification['user_id'],
                                       Friendship.friend_id == int(
                                           user_id)))).scalar() is not None if user_id is not None else False

                    friendship_request = db.session.query(FriendshipRequest).filter(
                        db.or_(db.and_(FriendshipRequest.requesting_id == int(user_id),
                                       FriendshipRequest.recipient_id == notification['user_id']),
                               db.and_(FriendshipRequest.requesting_id == notification['user_id'],
                                       FriendshipRequest.recipient_id == int(
                                           user_id)))).first() if user_id is not None else None

                    is_my_friend = {
                        'friendship': {'is_my_friend': is_my_friend, 'friendship_from_me': False,
                                       'friendship_to_me': False}}

                    if friendship_request:
                        if friendship_request.requesting_id == int(user_id):
                            is_my_friend['friendship']['friendship_from_me'] = True
                        else:
                            is_my_friend['friendship']['friendship_to_me'] = True

                    notification.update(is_my_friend)
                    notifications_dicts.append(notification)

                else:
                    notification = achievements_utils.formNotificationDict(user_id,
                                                                           int(notification["notification_type"].split('_')[1].replace('t', '')),
                                                                           int(notification["notification_type"].split(
                                                                               '_')[2].replace('l', '')),
                                                                           )
                    notification["notification_type"] = notification.pop("type")

                notification.update({"seconds_ago": int(time_diff.total_seconds())})
                notifications_dicts.append(notification)

            return json_200(notifications_dicts)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/edit_duels_exceptions', methods=['POST'])
def edit_duels_exceptions():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            exceptions = json['exceptions_data']

            for exception in exceptions:

                if exception['delete']:
                    exception = db.session.query(PrivacyDuelsException).filter_by(user_id=user_id,
                                                                                  exception_id=exception[
                                                                                      'exception_id']).delete()
                else:
                    if db.session.query(PrivacyDuelsException).filter_by(user_id=user_id,
                                                                         exception_id=exception[
                                                                             'exception_id']).scalar() is None:
                        exception = PrivacyDuelsException(user_id=user_id, exception_id=exception['exception_id'])
                        db.session.add(exception)

            duels_exceptions_count = db.session.query(PrivacyDuelsException.exception_id).filter_by(
                user_id=user_id).count() - len(exceptions)
            privacy_settings = db.session.query(PrivacySettings).filter_by(user_id=user_id).one()

            if duels_exceptions_count == 0 and privacy_settings.duels_invites_from == 'e':
                privacy_settings.duels_invites_from = 'n'
            elif privacy_settings.duels_invites_from != 'e':
                privacy_settings.duels_invites_from = 'e'

            db.session.commit()

            return Response(status=200)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/edit_privacy_settings', methods=['POST'])
def edit_privacy_settings():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            privacy_settings = db.session.query(PrivacySettings).filter_by(user_id=user_id).one()

            print(json)
            if json['privacy_settings'].get('duels_invites_from') is not None:
                privacy_settings.duels_invites_from = json['privacy_settings']['duels_invites_from']
            if json['privacy_settings'].get('show_in_ratings') is not None:
                privacy_settings.show_in_ratings = json['privacy_settings']['show_in_ratings']
            if json['privacy_settings'].get('profile_is_visible') is not None:
                privacy_settings.profile_is_visible = json['privacy_settings']['profile_is_visible']

            db.session.commit()
            return Response(status=200)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/send_friendship', methods=['POST'])
def send_friendship():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):

            if db.session.query(FriendshipRequest).filter(
                    db.or_(db.and_(FriendshipRequest.requesting_id == user_id,
                                   FriendshipRequest.recipient_id == json['friend_id']),
                           db.and_(FriendshipRequest.requesting_id == json['friend_id'],
                                   FriendshipRequest.recipient_id == user_id))).first() is None:
                friendship_request = FriendshipRequest(requesting_id=user_id, recipient_id=json['friend_id'])
                notification = Notification(user_id=json['friend_id'], id_user_from=user_id, notification_type='f',
                                            datetime_sent=datetime.utcnow())

                user_data = db.session.query(UserData).filter_by(user_id=int(user_id)).one()
                firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=json['friend_id']).all()
                db.session.query(UserData).filter_by(user_id=json['friend_id']).update(
                    dict(notifications_are_checked=False))

                last_friend_notification = db.session.query(Notification).filter_by(user_id=json['friend_id'],
                                                                                    id_user_from=user_id,
                                                                                    notification_type="f").order_by(
                    db.desc(Notification.datetime_sent)).first()

                hour_from_last_friend_request = (last_friend_notification is None) or (
                        divmod((notification.datetime_sent - last_friend_notification.datetime_sent).seconds, 3600)[
                            0] >= 1)

                if hour_from_last_friend_request:

                    for token_data in firebase_tokens:
                        content = {'type': 'f', 'user_name': user_data.user_name, 'user_id': str(user_id)}

                        if user_data.avatar_link:
                            content.update({'image_url': user_data.avatar_link})

                        try:
                            message = messaging.Message(data=content,
                                                        token=token_data.token)
                            messaging.send(message)
                        except Exception as e:
                            print(e)
                            db.session.delete(token_data)

                        db.session.add(notification)
                db.session.add(friendship_request)
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=400)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/accept_friendship', methods=['POST'])
def accept_friendship():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            if db.session.query(Friendship).filter(
                    db.or_(db.and_(Friendship.user_id == user_id, Friendship.friend_id == json['friend_id']),
                           db.and_(Friendship.user_id == json['friend_id'],
                                   Friendship.friend_id == user_id))).scalar() is None:

                friendship = Friendship(user_id=user_id, friend_id=json['friend_id'], datetime_added=datetime.utcnow())

                friendship_request = db.session.query(FriendshipRequest).filter(db.or_(
                    db.and_(FriendshipRequest.requesting_id == int(user_id),
                            FriendshipRequest.recipient_id == json['friend_id']),
                    db.and_(FriendshipRequest.requesting_id == json['friend_id'],
                            FriendshipRequest.recipient_id == int(user_id))))

                if friendship_request.first():
                    request_notification = db.session.query(Notification).filter_by(user_id=user_id,
                                                                                    id_user_from=json['friend_id'],
                                                                                    notification_type='f')
                    notification = Notification(user_id=json['friend_id'], id_user_from=user_id, notification_type='a',
                                                datetime_sent=datetime.utcnow())

                    user_data = db.session.query(UserData).filter_by(user_id=int(user_id)).one()
                    firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=json['friend_id']).all()
                    db.session.query(UserData).filter_by(user_id=json['friend_id']).update(
                        dict(notifications_are_checked=False))

                    for token_data in firebase_tokens:
                        content = {'type': 'a', 'user_name': user_data.user_name, 'user_id': str(user_id)}

                        if user_data.avatar_link:
                            content.update({'image_url': user_data.avatar_link})

                        try:
                            message = messaging.Message(data=content,
                                                        token=token_data.token)
                            messaging.send(message)
                        except Exception as e:
                            print(e)
                            db.session.delete(token_data)

                    if db.session.query(Friendship).filter(db.or_(Friendship.user_id == user_id, Friendship.friend_id == user_id)).first() is None:
                        achievements_utils.giveNonImprovableAchievementByType(achievements_utils.TYPE_FRIEND_ADD, user_id, db)

                    if db.session.query(Friendship).filter(db.or_(Friendship.user_id == json['friend_id'], Friendship.friend_id == json['friend_id'])).first() is None:
                        achievements_utils.giveNonImprovableAchievementByType(achievements_utils.TYPE_FRIEND_ADD, json['friend_id'], db)

                    request_notification.delete()
                    friendship_request.delete()
                    db.session.add(friendship)
                    db.session.add(notification)
                    db.session.commit()
                    return Response(status=200)
                else:
                    return Response(status=400)
            else:
                return Response(status=400)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/reject_friendship', methods=['POST'])
def reject_friendship():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            friendship_request = db.session.query(FriendshipRequest).filter(db.or_(
                db.and_(FriendshipRequest.requesting_id == int(user_id),
                        FriendshipRequest.recipient_id == json['friend_id']),
                db.and_(FriendshipRequest.requesting_id == json['friend_id'],
                        FriendshipRequest.recipient_id == int(user_id))))
            request_notification = db.session.query(Notification).filter_by(user_id=user_id,
                                                                            id_user_from=json['friend_id'],
                                                                            notification_type='f')
            if friendship_request.first():

                user_data = db.session.query(UserData).filter_by(user_id=int(user_id)).one()
                firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=json['friend_id']).all()

                for token_data in firebase_tokens:
                    content = {'type': 'r', 'user_name': user_data.user_name, 'user_id': str(user_id)}

                    if user_data.avatar_link:
                        content.update({'image_url': user_data.avatar_link})
                    try:
                        message = messaging.Message(data=content,
                                                    token=token_data.token)
                        messaging.send(message)
                    except Exception as e:
                        print(e)
                        db.session.delete(token_data)

                friendship_request.delete()
                request_notification.delete()
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=400)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            friend = db.session.query(Friendship).filter(
                db.or_(db.and_(Friendship.user_id == int(user_id), Friendship.friend_id == json['friend_id']),
                       db.and_(Friendship.user_id == json['friend_id'], Friendship.friend_id == int(user_id))))
            duels_exception = db.session.query(PrivacyDuelsException).filter_by(user_id=int(user_id),
                                                                                exception_id=json['friend_id']).first()
            if friend.first():
                if duels_exception:
                    db.session.delete(duels_exception)

                user_data = db.session.query(UserData).filter_by(user_id=int(user_id)).one()
                firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=json['friend_id']).all()

                for token_data in firebase_tokens:
                    content = {'type': 'r', 'user_name': user_data.user_name, 'user_id': str(user_id)}

                    if user_data.avatar_link:
                        content.update({'image_url': user_data.avatar_link})
                    try:
                        message = messaging.Message(data=content,
                                                    token=token_data.token)
                        messaging.send(message)
                    except Exception as e:
                        print(e)
                        db.session.delete(token_data)

                friend.delete()
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=400)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/cancel_friendship', methods=['POST'])
def cancel_friendship():
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            friendship_request = db.session.query(FriendshipRequest).filter(
                db.or_(
                    db.and_(FriendshipRequest.requesting_id == int(user_id),
                            FriendshipRequest.recipient_id == json['friend_id']),
                    db.and_(FriendshipRequest.requesting_id == json['friend_id'],
                            FriendshipRequest.recipient_id == int(user_id))))
            request_notification = db.session.query(Notification).filter_by(user_id=json['friend_id'],
                                                                            id_user_from=user_id,
                                                                            notification_type='f')
            if friendship_request.first():

                user_data = db.session.query(UserData).filter_by(user_id=int(user_id)).one()
                firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=json['friend_id']).all()
                db.session.query(UserData).filter_by(user_id=json['friend_id']).update(
                    dict(notifications_are_checked=True))

                for token_data in firebase_tokens:
                    content = {'type': 'c', 'user_name': user_data.user_name, 'user_id': str(user_id)}

                    if user_data.avatar_link:
                        content.update({'image_url': user_data.avatar_link})
                    try:
                        message = messaging.Message(data=content,
                                                    token=token_data.token)
                        messaging.send(message)
                    except Exception as e:
                        print(e)
                        db.session.delete(token_data)

                request_notification.delete()
                friendship_request.delete()
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=400)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/authentication', methods=['POST'])
def check_correct_token():
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']
        return Response(str(check_token(user_id, token) is not None).lower(), status=200)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/send_exercise_report', methods=['POST'])
def save_exercise_report():
    try:
        json = request.get_json()

        is_logged_in = json.get('auth_data') is not None

        if is_logged_in:
            user_id = json['auth_data']['user_id']
            token = json['auth_data']['user_token']

        if not is_logged_in or check_token(user_id, token):
            exercise_number = json["report_data"]['exercise_number']
            bug_types = json["report_data"]['bugs']

            for bug_type in bug_types:
                db.session.add(ExerciseReport(user_id=None if not is_logged_in else user_id, bug_type=bug_type,
                                              exercise_number=exercise_number))

            db.session.commit()

            return Response(status=200)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/send_interesting_like', methods=['POST'])
def save_interesting_like():
    try:
        json = request.get_json()

        is_logged_in = json.get('auth_data') is not None

        if is_logged_in:
            user_id = json['auth_data']['user_id']
            token = json['auth_data']['user_token']

        if not is_logged_in or check_token(user_id, token):
            interesting_number = json["like_data"]['interesting_number']
            like_it = json["like_data"]['like_it']

            db.session.add(
                InterestingLike(user_id=None if not is_logged_in else user_id, interesting_number=interesting_number,
                                like_it=like_it))

            db.session.commit()

            return Response(status=200)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/has_friends', methods=['GET'])
def has_friends():
    try:
        user_id = int(request.args.get('user_id'))
        friends_count = db.session.query(Friendship).filter(
            db.or_(Friendship.user_id == user_id, Friendship.friend_id == user_id)).count()
        return Response(str(friends_count != 0).lower(), status=200)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/get_users', methods=['GET'])
def get_users():
    try:

        user_id = request.args.get('user_id')
        friend_of_user_id = request.args.get('friend_of_user_id')

        sort = request.args.get('sort_by')
        starts_with = request.args.get('starts_with')

        per_page = int(request.args.get("per_page"))
        page_number = int(request.args.get("page_number"))

        global_search = friend_of_user_id is None

        friends_count = db.session.query(User).count()

        if not global_search:
            friends_sort = None

            friends_query = db.session.query(UserData.user_id, UserData.user_name, UserData.avatar_link) \
                .outerjoin(Friendship,
                           db.or_(Friendship.user_id == UserData.user_id, Friendship.friend_id == UserData.user_id)) \
                .filter(db.or_(Friendship.user_id == int(friend_of_user_id if friend_of_user_id else user_id),
                               Friendship.friend_id == int(friend_of_user_id if friend_of_user_id else user_id))) \
                .filter(UserData.user_id != int(friend_of_user_id if friend_of_user_id else user_id))

            friends_count = db.session.query(Friendship).filter(
                db.or_(Friendship.user_id == friend_of_user_id, Friendship.friend_id == friend_of_user_id)).count()

            if friends_count == 0:
                return json_200({'users_count': 0, 'users': []})

            if sort == "new_to_old":
                friends_sort = db.desc(Friendship.datetime_added)
            elif sort == "old_to_new":
                friends_sort = db.asc(Friendship.datetime_added)

            if friends_sort is None:

                if sort == "A_to_Z":
                    friends_sort = db.asc(UserData.user_name)
                elif sort == "Z_to_A":
                    friends_sort = db.desc(UserData.user_name)

                else:

                    if starts_with:
                        user_name = starts_with.replace('@', '')
                        friends_query = friends_query.filter(
                            db.or_(UserData.user_name.ilike(user_name + '%'), UserData.name.ilike(user_name + '%')))

            if friends_sort is not None:
                friends_query = friends_query.order_by(friends_sort)

            users = friends_query.paginate(page_number, per_page, False).items

        else:

            friends_ids_subquery = db.session.query(UserData.user_id) \
                .outerjoin(Friendship,
                           db.or_(Friendship.user_id == UserData.user_id, Friendship.friend_id == UserData.user_id)) \
                .filter(db.or_(Friendship.user_id == int(user_id), Friendship.friend_id == int(user_id))) \
                .filter(UserData.user_id != int(user_id)) \
                .subquery()

            users_query = db.session.query(UserData.user_id, UserData.user_name, UserData.avatar_link) \
                .outerjoin(PrivacySettings, UserData.user_id == PrivacySettings.user_id) \
                .filter(UserData.user_id.notin_(friends_ids_subquery)) \
                .filter(PrivacySettings.profile_is_visible.is_(True))

            if starts_with:
                user_name = starts_with.replace('@', '')
                users_query = users_query.filter(
                    db.or_(UserData.user_name.ilike(user_name + '%'), UserData.name.ilike(user_name + '%')))

            users = users_query.paginate(page_number, per_page, False).items

        users = [dict(zip(["user_id", "user_name", "avatar_link"], friend)) for friend in
                 users]

        for user in users:
            is_my_friend = db.session.query(Friendship).filter(
                db.or_(db.and_(Friendship.user_id == int(user_id),
                               Friendship.friend_id == user['user_id']),
                       db.and_(Friendship.user_id == user['user_id'],
                               Friendship.friend_id == int(
                                   user_id)))).scalar() is not None if user_id is not None else False

            friendship_request = db.session.query(FriendshipRequest).filter(
                db.or_(db.and_(FriendshipRequest.requesting_id == int(user_id),
                               FriendshipRequest.recipient_id == user['user_id']),
                       db.and_(FriendshipRequest.requesting_id == user['user_id'],
                               FriendshipRequest.recipient_id == int(
                                   user_id)))).first() if user_id is not None else None

            is_my_friend = {
                'friendship': {'is_my_friend': is_my_friend, 'friendship_from_me': False, 'friendship_to_me': False}}

            if friendship_request:
                if friendship_request.requesting_id == int(user_id):
                    is_my_friend['friendship']['friendship_from_me'] = True
                else:
                    is_my_friend['friendship']['friendship_to_me'] = True

            user.update(is_my_friend)

        response = {'users_count': friends_count, 'users': users}
        return json_200(response)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/notifications_are_checked', methods=['POST'])
def notifications_are_checked():
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']
        if check_token(user_id, token):
            db.session.query(UserData).filter_by(user_id=user_id).update(
                dict(notifications_are_checked=True))
            db.session.commit()
            return Response(status=200)
        else:
            return Response(status=400)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/achievements_data', methods=['GET'])
def get_achievements_data():
    try:
        user_id = int(request.args.get('user_id')) if request.args.get('user_id') else None
        only_completed = str2bool(request.args.get('completed')) if request.args.get('completed') else False
        db_achievements = as_dict_array(db.session.query(Achievement).filter_by(user_id=user_id).all()) if user_id else []
        response_achievements = copy.deepcopy(achievements)
        completed_achievements = []
        for achievement in response_achievements:
            if not achievement["improvable"]:
                achievement.update(dict(completed=any((user_achievement["type"] == achievement["type"] and user_achievement.get("level") == 1) for user_achievement  in db_achievements)))
            else:

                database_achievement = list(filter(lambda user_achievement: user_achievement["type"] == achievement["type"], db_achievements))
                database_achievement = database_achievement[0] if len(database_achievement) > 0 else None

                current_level = 0 if not database_achievement else database_achievement["level"]

                array_item_index = current_level-1 if(current_level == achievement["max_level"]) else current_level

                achievement.update(dict(current_level=0 if not database_achievement else database_achievement["level"],
                                        exercise=achievement["exercise"][current_level],
                                        current_progress=achievements_utils.getAchievementProgressByType(achievement["type"], user_id, db),
                                        max_progress=achievement["max_progress"][array_item_index],
                                        reward=achievement["reward"][array_item_index],
                                        current_level_icon=achievement["icon_url"][array_item_index-1 if current_level != achievement["max_level"] else array_item_index] if array_item_index > 0 else None,
                                        next_level_icon=achievement["icon_url"][array_item_index] if current_level != achievement["max_level"] else None,
                                        ))
                del achievement["icon_url"]

        if only_completed:
            for response_achievement in response_achievements:
                if (response_achievement.get("current_level")  and response_achievement.get("current_level") != 0) or response_achievement.get("completed"):
                    completed_achievements.append(response_achievement)
        return json_200(completed_achievements if only_completed else response_achievements)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/achievements', methods=['GET'])
def get_achievements():
    try:
        user_id = int(request.args.get('user_id'))
        db_achievements = as_dict_array(db.session.query(Achievement).filter_by(user_id=user_id).all())
        response_list = []
        for db_achievement in db_achievements:
            if db_achievement["level"] != 0:
                achievement_data = list(filter(lambda achievement: achievement["type"] == db_achievement["type"], achievements))[0]
                if not achievement_data["improvable"]:
                    db_achievement.update(dict(icon_url=achievement_data["icon_url"], improvable=False))
                else:
                    db_achievement.update(dict(icon_url=achievement_data["icon_url"][db_achievement["level"]-1], improvable=True))
                response_list.append(db_achievement)
        return json_200(response_list)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/is_my_friend', methods=['GET'])
def check_is_my_friend():
    try:
        my_id = int(request.args.get('my_id'))
        user_id = int(request.args.get('user_id'))
        is_my_friend = db.session.query(Friendship.friend_id, Friendship.datetime_added).filter(
            db.or_(db.and_(Friendship.user_id == my_id,
                           Friendship.friend_id == user_id),
                   db.and_(Friendship.user_id == user_id,
                           Friendship.friend_id == my_id))).scalar() is not None

        friendship_request = db.session.query(FriendshipRequest).filter(
            db.or_(db.and_(FriendshipRequest.requesting_id == my_id,
                           FriendshipRequest.recipient_id == user_id),
                   db.and_(FriendshipRequest.requesting_id == user_id,
                           FriendshipRequest.recipient_id == my_id))).first()
        response = {'is_my_friend': is_my_friend, 'friendship_from_me': False, 'friendship_to_me': False}
        if friendship_request:
            if friendship_request.requesting_id == my_id:
                response['friendship_from_me'] = True
            else:
                response['friendship_to_me'] = True
        return json_200(response)
    except Exception as e:
        print(e)
        return Response(status=400)


def encrypt(string):
    return str(bcrypt.hashpw(bytes(string, utf), bcrypt.gensalt(10)), utf)


def check_bcrypt(str, hash_str):
    return bcrypt.checkpw(bytes(str, utf), bytes(hash_str, utf))


def generate_token():
    randomSource = string.ascii_letters + string.digits + string.punctuation
    password = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)
    password += random.choice(string.punctuation)
    for i in range(64):
        password += random.choice(randomSource)
    passwordList = list(password)
    random.SystemRandom().shuffle(passwordList)
    password = ''.join(passwordList)
    return password


def check_token(user_id, user_token):
    return db.session.query(UserToken).filter_by(user_id=user_id, user_token=user_token).first()


def number_bounds(number, array):
    return json_200(array[int(number) - 1]) if (int(number) <= len(array)) and (int(number) > 0) else Response(
        status=404)


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def calc_operators(components, result):
    operators = ['-', '+', '÷', '×']
    for operator in operators:
        if eval_with_replace(components[0] + operator + components[1]) == int(result):
            return operator


def eval_with_replace(equation, round_to_int=True):
    return int(eval(replace_operators(equation))) if round_to_int else eval(replace_operators(equation))


def inverse_number_operator(number):
    if '-' in number:
        return number.replace('-', '+')
    else:
        return '-' + number


def solve_x(equation):
    equation = replace_operators(equation)
    x = Symbol('x')
    return solve(equation, x)[0]


def json_200(body):
    resp = jsonify(body), 200
    resp[0].mimetype = 'application/json, charset=utf-8'
    return resp


def get_numbers_count(numbers, natural):
    count = 0
    for number in numbers:
        if (number != '0') and (number != '∞') and ('.' not in number) and ('-' not in number):
            if natural:
                count = count + 1
            else:
                count = count + 1
    return count


def convert_datetime_str(datetimestr):
    return datetime.strptime(datetimestr, '%a, %d %b %Y %H:%M:%S')


def replace_operators(equation):
    equation = equation.replace(":", "/")
    equation = equation.replace("÷", "/")
    equation = equation.replace("×", "*")
    return equation


def create_new_user(user_email, user_password, unregistered_user_data_json, avatar_url):
    hash_password = encrypt(user_password) if user_password else None
    user_name = form_user_name(user_email)

    if user_utils.match_user_name(user_name):

        new_user = User(user_email=user_email, user_type='s' if hash_password else 'g',
                        datetime_added=datetime.utcnow(),
                        user_password=hash_password)
        db.session.add(new_user)
        db.session.flush()

        print(unregistered_user_data_json)
        if "user_data" in unregistered_user_data_json:
            user_data = UserData(user_id=new_user.user_id, user_public_id=uuid.uuid1(), user_name=user_name,
                                 current_level=unregistered_user_data_json["user_data"]["current_level"],
                                 current_level_XP=unregistered_user_data_json["user_data"]["current_level_XP"],
                                 streak_days=unregistered_user_data_json["user_data"]["streak_days"],
                                 streak_datetime=convert_datetime_str(
                                     unregistered_user_data_json["user_data"]["streak_datetime"]),
                                 completed_parts=unregistered_user_data_json["user_data"]["completed_parts"],
                                 avatar_link=avatar_url)
        else:
            user_data = UserData(user_id=new_user.user_id, user_public_id=uuid.uuid1(), user_name=user_name,
                                 avatar_link=avatar_url)
        db.session.add(user_data)

        if "user_statistics" in unregistered_user_data_json:
            for stat in unregistered_user_data_json['user_statistics']:
                stat.update({'user_id': new_user.user_id})
                user_stat = UserStatistics(**stat)
                user_stat.datetime = convert_datetime_str(user_stat.datetime)
                db.session.add(user_stat)

        privacy_settings = PrivacySettings(user_id=new_user.user_id)
        db.session.add(privacy_settings)
        db.session.commit()

        # thread = threading.Thread(target=send_mail.send_mail, args=(user_email,))
        # thread.start()
        return user_data
    else:
        return None


def form_user_name(email):
    user_name = email.split('@')[0]

    if len(user_name) > user_utils.MAX_USER_NAME_LENGTH:
        user_name = user_name[:user_utils.MAX_USER_NAME_LENGTH]

    user_name_is_smaller = len(user_name) < user_utils.MIN_USER_NAME_LENGTH
    user_name_missing_chars_count = max(user_utils.MIN_USER_NAME_LENGTH - len(user_name), 0)

    if user_name_is_smaller:
        user_name = user_name + ("0" * user_name_missing_chars_count)

    i = 1
    while db.session.query(UserData).filter_by(user_name=user_name).scalar() is not None:

        user_name = (user_name[:len(user_name) - user_name_missing_chars_count] if user_name_is_smaller else user_name[
                                                                                                             :len(
                                                                                                                 user_name) - (
                                                                                                                  len(
                                                                                                                      str(
                                                                                                                          i - 1)) if i - 1 > 0 else 0)]) + str(
            i)

        user_name_is_smaller = len(user_name) < user_utils.MIN_USER_NAME_LENGTH

        if user_name_is_smaller:
            user_name = user_name[:len(user_name) - len(str(i))] + (
                    "0" * max(user_utils.MIN_USER_NAME_LENGTH - len(user_name), 0)) + str(i)

        if len(user_name) > user_utils.MAX_USER_NAME_LENGTH:
            len_diff = len(user_name) - user_utils.MAX_USER_NAME_LENGTH
            user_name = user_name[:len(user_name) - (len(str(i)) + len_diff)] + str(i)

        i = i + 1

    return user_name


def create_firebase_token(user_id, json):
    if "push_data" in json:
        firebase_token = FirebaseToken(user_id=user_id, token=json['push_data']['token'],
                                       device_id=json['push_data']['device_id'])

        db.session.query(FirebaseToken).filter_by(device_id=firebase_token.device_id).delete()
        if db.session.query(FirebaseToken).filter_by(user_id=firebase_token.user_id,
                                                     token=firebase_token.token,
                                                     device_id=firebase_token.device_id).scalar() is None:
            db.session.add(firebase_token)


def create_token(user_id, device_id):
    token = generate_token()

    old_tokens = db.session.query(UserToken).filter_by(user_id=user_id, device_id=device_id)

    old_tokens.delete()

    new_token = UserToken(user_id=user_id, user_token=token, device_id=device_id)

    db.session.add(new_token)
    return token

CORS(app)
