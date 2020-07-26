from flask import jsonify, request, Response
import flask
import bcrypt
import firebase_admin
import firebase_admin.messaging as messaging
from firebase_admin import credentials
from smtp import send_mail
import threading
import re
import os
import time as t
from itertools import chain
import string
import operator
import random
from sqlalchemy import func
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
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

utf = 'UTF-8'
CLIENT_ID = "100888478237-lldqud6eng1l50k3isp1ovkvl18ev34i.apps.googleusercontent.com"

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

cred = credentials.Certificate("serviceAccountKey.json")
default_app = firebase_admin.initialize_app(cred)

with open('dict/levels_dict', 'r', encoding='utf-8') as f:
    levels = f.read()
    levels = j.loads(levels)

with open('dict/chapters_dict', 'r', encoding='utf-8') as f:
    chapters = f.read()
    chapters = j.loads(chapters)

with open('dict/interesting_dict', 'r', encoding='utf-8') as f:
    interesting_list = f.read()
    interesting_list = j.loads(interesting_list)

with open('dict/exercises_dict', 'r', encoding='utf-8') as f:
    exercises = f.read()
    exercises = j.loads(exercises)

with open('dict/offline_exercises_dict', 'r', encoding='utf-8') as f:
    offline_exercises_diff = f.read()
    offline_exercises_diff = j.loads(offline_exercises_diff)

unLoggedLevels = copy.deepcopy(levels)
unLoggedLevels = unLoggedLevels[:2]
unLoggedLevels[1]["children"].insert(0, {"type": "subscribe",
                                         "title": "Войдите, чтобы разблокировать ещё 120 заданий",
                                         "button": ["Войти"]})

message = messaging.Message(data={'type': 'a', 'user_name': "shevtsov", 'user_id': str(2)},
                            token="fRl2tjMWTHqgXYgcRMiKFp:APA91bH0EfMdPCiFxgjZ6seIybndkvnj-gmR8dl3zpW2gkVOZzbZpS2iCnqXwe0HQ-OeHbK8KP-nRuVyhEXwlzJFKaxM_aye0SCg5DEdNWlos4XKBPXQ_ybaWEsQe1_EIlBmbvp6AMRQ")
messaging.send(message)

exercises_flatten = []
for idx, chapter_part in enumerate(exercises):
    for idx1, exercise in enumerate(chapter_part['exercises']):
        if exercise['type'] == 'exercise':
            exercises_flatten.append(exercise)


@app.route('/levels', methods=['GET'])
def get_levels():
    print(request.headers)
    print(request.data)
    return json_200(levels if str2bool(request.args.get('logged_in')) else unLoggedLevels)


@app.route('/levels/<number>', methods=['GET'])
def get_level(number):
    print(request.headers)
    print(request.data)
    return number_bounds(number, levels)


@app.route('/chapters', methods=['GET'])
def get_chapters():
    print(request.headers)
    print(request.data)
    return json_200(chapters)


@app.route('/chapters/<number>', methods=['GET'])
def get_chapter(number):
    print(request.headers)
    print(request.data)
    return number_bounds(number, chapters)


@app.route('/chapter_parts/<number>', methods=['GET'])
def get_exercises(number):
    print(request.headers)
    print(request.data)
    return number_bounds(number, exercises)


@app.route('/offline_exercises', methods=['GET'])
def get_offline_exercises():
    print(request.headers)
    print(request.data)
    return json_200(offline_exercises)


@app.route('/exercises/<number>', methods=['GET', 'POST'])
def get_exercise(number):
    print(request.headers)
    print(request.data)
    if request.method == 'GET':
        return number_bounds(number, exercises_flatten)
    elif request.method == 'POST':
        try:
            array_index = int(number) - 1
            current_exercise = exercises_flatten[array_index]
            answer = request.get_json()
            if current_exercise['exercise_type'] == 1:
                for d in current_exercise['exercise_info']['variants']:
                    if current_exercise['exercise_info']['title'] in d:
                        correct_answer = d
                return json_200({'result': 'true'} if current_exercise['exercise_info']['title'] == answer['answer']
                                else {'result': 'false', 'description': {'description_type': 'shape',
                                                                         'description_content': correct_answer}})
            elif current_exercise['exercise_type'] == 2 or current_exercise['exercise_type'] == 4:
                return json_200({'result': 'true'} if current_exercise['exercise_info']['title'][1] == answer['answer']
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content':
                                                                             current_exercise['exercise_info']['title'][
                                                                                 1]}})
            elif current_exercise['exercise_type'] == 3:
                return json_200({'result': 'true'} if current_exercise['exercise_info']['title'][1] == answer['answer']
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content':
                                                                             current_exercise['exercise_info']['title'][
                                                                                 0]}})
            elif current_exercise['exercise_type'] == 5:
                title_number = int(current_exercise['exercise_info']['title'].split(' ')[0])
                if title_number == eval(answer['answer']):
                    return json_200({'result': 'true'})
                else:
                    for variant in current_exercise['exercise_info']['variants']:
                        if eval(variant) == title_number:
                            return json_200({'result': 'false', 'description': {'description_type': 'text',
                                                                                'description_content':
                                                                                    variant}})
            elif current_exercise['exercise_type'] == 6:
                title_result = eval(current_exercise['exercise_info']['title'].split('=')[0])
                print(current_exercise['exercise_info']['title'].split('=')[0])
                return json_200({'result': 'true'} if title_result == int(answer['answer'])
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content':
                                                                             str(title_result)}})
            elif current_exercise['exercise_type'] == 7:
                equation_parts = current_exercise['exercise_info']['title'].split('=')
                equation_result = eval(equation_parts[0]) == eval(equation_parts[1])
                return json_200({'result': 'true'} if equation_result == str2bool(answer['answer'])
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': str(
                                                                             equation_result).lower()}})
            elif current_exercise['exercise_type'] == 8:
                parts = current_exercise['exercise_info']['title'].replace('...', 'x').replace(' ', '').split('=')
                result = solve_x(parts[0] + inverse_number_operator(parts[1]))
                return json_200({'result': 'true'} if result == int(answer['answer'])
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': str(result)}})
            elif current_exercise['exercise_type'] == 9:
                answer_result = eval(answer['answer'])
                return json_200({'result': 'true'} if answer_result == int(
                    current_exercise['exercise_info']['title'].replace('=', ''))
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': str(answer_result)}})
            elif current_exercise['exercise_type'] == 10:
                result = solve_x(current_exercise['exercise_info']['title_parts'][0] + 'x' + inverse_number_operator(
                    current_exercise['exercise_info']['title_parts'][1].replace('=', '')))
                return json_200({'result': 'true'} if result == int(answer['answer'])
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': str(result)}})
            elif current_exercise['exercise_type'] == 11:
                int_parts = list(map(int, current_exercise['exercise_info']['title_parts']))
                compare_to_number = int(current_exercise['exercise_info']['compare_number'])
                filter = current_exercise['exercise_info']['filter']
                if filter == "bigger":
                    result = [x > compare_to_number for x in int_parts]
                elif "lower":
                    result = [x < compare_to_number for x in int_parts]
                result = result.count(True)
                return json_200({'result': 'true'} if result == int(answer['answer'])
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': str(result)}})
            elif current_exercise['exercise_type'] == 12:
                parts = current_exercise['exercise_info']['title'].replace('...', 'x').replace(' ', '').split('=')
                for variant in current_exercise['exercise_info']['variants']:
                    if eval(parts[0].replace('x', variant)) == int(parts[1]):
                        true_variant = variant
                result = eval(parts[0].replace('x', answer['answer']))
                return json_200({'result': 'true'} if result == int(parts[1])
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': true_variant}})
            elif current_exercise['exercise_type'] == 13:
                true_answer = str(eval(current_exercise['exercise_info']['title'][1]))
                return json_200({'result': 'true'} if answer['answer'] == true_answer
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': true_answer}})
            elif current_exercise['exercise_type'] == 14:
                title_number = int(current_exercise['exercise_info']['title'][1])
                if title_number == eval(answer['answer']):
                    return json_200({'result': 'true'})
                else:
                    for variant in current_exercise['exercise_info']['variants']:
                        if eval(variant) == title_number:
                            return json_200({'result': 'false', 'description': {'description_type': 'text',
                                                                                'description_content':
                                                                                    variant}})
            elif current_exercise['exercise_type'] == 15:
                title_number = int(current_exercise['exercise_info']['title'])
                true_answers = []
                for variant in current_exercise['exercise_info']['variants']:
                    if eval(variant) == title_number:
                        true_answers.append(variant)
                answers = answer['answer'].split(',')
                return json_200({'result': 'true'} if set(answers) == set(true_answers)
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': ','.join(true_answers)}})
            elif current_exercise['exercise_type'] == 16:
                equation_parts = [current_exercise['exercise_info']['title_parts'][0],
                                  current_exercise['exercise_info']['title_parts'][1].split('=')[0]]
                equation_result = current_exercise['exercise_info']['title_parts'][1].split('=')[1]
                true_answer = calc_operators(equation_parts, equation_result)
                return json_200({'result': 'true'} if replace_operators(answer['answer']) == true_answer
                                else {'result': 'false', 'description': {'description_type': 'text',
                                                                         'description_content': true_answer}})
            elif current_exercise['exercise_type'] == 17:
                equation_result = str(eval(current_exercise['exercise_info']['title'][1]))
                return json_200({'result': 'true'} if answer['answer'] == equation_result
                                else {'result': 'false', 'description': {'description_type': 'shape',
                                                                         'description_content': [current_exercise['exercise_info']['title'][0], equation_result]}})
        except Exception as e:
            print(e)
            return Response(status=400)


@app.route('/interesting/<number>', methods=['GET'])
def get_interesting(number):
    print(request.headers)
    print(request.data)
    return number_bounds(number, interesting_list)


@app.route('/interesting', methods=['GET'])
def get_interesting_list():
    print(request.headers)
    print(request.data)
    return json_200(interesting_list)


@app.route('/user_data', methods=['GET'])
def get_user_data():
    print(request.headers)
    print(request.data)
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
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
            percent = json['completed_exercises_data']['percent']
            chapter_number = json['completed_exercises_data']['chapter_number']
            chapter_part_number = json['completed_exercises_data']['chapter_part_number']
            obtained_time = json['completed_exercises_data']['obtained_time']
            completed_datetime = convert_datetime_str(json['completed_exercises_data']['datetime'])

            is_training = user_data.completed_parts[chapter_number - 1] >= chapter_part_number

            obtained_XP = level_utils.get_obtained_XP(user_data, percent, is_training, db, completed_datetime.date())
            new_levels_count = level_utils.get_new_levels_count(user_data, obtained_XP)
            new_level_XP = level_utils.get_new_level_XP(user_data, obtained_XP)

            if not is_training:
                new_completed_parts = user_data.completed_parts.copy()
                new_completed_parts[chapter_number - 1] += 1
                user_data.completed_parts = new_completed_parts

            user_data.current_level = UserData.current_level + new_levels_count
            user_data.current_level_XP = new_level_XP

            if (completed_datetime.date() - timedelta(days=1)) >= user_data.streak_datetime.date():
                if (completed_datetime.date() - timedelta(days=1)) > user_data.streak_datetime.date():
                    user_data.streak_days = 1
                else:
                    user_data.streak_days = UserData.streak_days + 1
                user_data.streak_datetime = completed_datetime

            user_stat = UserStatistics(user_id=user_id)

            user_stat.datetime = completed_datetime

            if is_training:
                user_stat.obtained_trainings = 1
            else:
                user_stat.obtained_exercises = 1

            user_stat.obtained_XP = obtained_XP
            user_stat.obtained_time = obtained_time

            db.session.add(user_stat)

            db.session.commit()
            return Response(status=200)
        else:
            return Response(status=404)

    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    print(request.headers)
    print(request.data)
    try:
        json = j.loads(request.form.to_dict()['json'])
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
            if user_utils.user_name_not_exists(db, json['user_data']['user_name'], user_data.user_name):
                if user_utils.is_valid_edit_profile_data(json['user_data']['user_name'],
                                                         json['user_data'].get('user_full_name', None)):
                    if 'avatar' in request.files:
                        file_name = uuid.uuid1().hex
                        file_name = '{0}.jpg'.format(file_name)
                        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                        if user_data.avatar_link:
                            try:
                                os.remove("{0}/{1}".format(app.config['UPLOAD_FOLDER'],
                                                           user_data.avatar_link.split("avatars/")[1]))
                            except:
                                {}
                        request.files['avatar'].save(full_filename)
                        user_data.avatar_link = "http://37.53.93.223:5037/static/avatars/{0}".format(file_name)
                    else:
                        user_data.avatar_link = json['user_data'].get('avatar_link', None)
                    if json['user_data']['user_name'].isalnum():
                        user_data.user_name = json['user_data']['user_name']
                    else:
                        return Response(status=400)
                    user_data.user_full_name = json['user_data'].get('user_full_name', None)
                    db.session.commit()
                    return json_200({"avatar_link": user_data.avatar_link})
                else:
                    return Response(status=400)
            else:
                return Response(status=409)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/is_user_name_available', methods=['GET'])
def is_user_name_available():
    print(request.headers)
    print(request.data)
    try:
        t.sleep(0.1)
        return Response(
            str(not db.session.query(UserData).filter_by(user_name=request.args.get('user_name')).scalar()).lower(),
            status=200)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/user_statistics/<time>', methods=['GET'])
def get_user_statistics_by_time(time):
    print(request.headers)
    print(request.data)
    try:
        user_id = request.args.get("user_id")
        labels = ["obtained_XP", "obtained_time", "obtained_exercises", "obtained_trainings", "obtained_achievements"]

        today = convert_datetime_str(request.headers['Date']).date()
        yesterday = today - timedelta(days=1)
        week = today - timedelta(days=7)
        month = today - timedelta(days=30)

        today_filter = func.DATE(UserStatistics.datetime) == today
        yesterday_filter = func.DATE(UserStatistics.datetime) == yesterday
        week_filter = func.DATE(UserStatistics.datetime) >= week
        month_filter = func.DATE(UserStatistics.datetime) >= month

        query = db.session.query(db.func.coalesce(db.func.sum(UserStatistics.obtained_XP), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_time), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_exercises), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_trainings), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_achievements), 0)) \
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
            results_dict = dict(zip(labels, int_results))
            results_dict.update({"time_type": time})
            return json_200(results_dict)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/user_statistics', methods=['GET'])
def get_user_statistics():
    print(request.headers)
    print(request.data)
    try:
        user_id = request.args.get("user_id")
        times = ["today", "yesterday", "week", "month"]
        labels = ["obtained_XP", "obtained_time", "obtained_exercises", "obtained_trainings",
                  "obtained_achievements"]

        today = convert_datetime_str(request.headers['Date']).date()
        yesterday = today - timedelta(days=1)
        week = today - timedelta(days=7)
        month = today - timedelta(days=30)

        today_filter = func.DATE(UserStatistics.datetime) == today
        yesterday_filter = func.DATE(UserStatistics.datetime) == yesterday
        week_filter = func.DATE(UserStatistics.datetime) >= week
        month_filter = func.DATE(UserStatistics.datetime) >= month

        query = db.session.query(db.func.coalesce(db.func.sum(UserStatistics.obtained_XP), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_time), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_exercises), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_trainings), 0),
                                 db.func.coalesce(db.func.sum(UserStatistics.obtained_achievements), 0)) \
            .filter_by(user_id=user_id)

        results_array = [query.filter(today_filter)[0], query.filter(yesterday_filter)[0], query.filter(week_filter)[0],
                         query.filter(month_filter)[0]]

        results_dict_array = []
        if results_array:
            for idx, results in enumerate(results_array):
                int_results = (int(result) for result in results)
                results_dict = dict(zip(labels, int_results))
                results_dict.update({'time_type': times[idx]})
                results_dict_array.append(results_dict)
            return json_200(results_dict_array)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/sign_in_with_google', methods=['POST'])
def sign_in_with_google():
    print(request.headers)
    print(request.data)
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
                user_data = create_new_user(user_email, None, json)
            else:
                user_data = db.session.query(UserData).filter_by(user_id=user.user_id).one()

            token = create_token(user.user_id, json['push_data']['device_id'])
            create_firebase_token(user.user_id, json)

            db.session.commit()
            return json_200(
                {**{'user_id': user.user_id, 'user_token': token}, "user_data": {**as_dict(user_data)}})
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/sign_up', methods=['POST'])
def sign_up():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_email = json['user_email']
        user_password = json['user_password']
        if (len(user_password) < 6) or (not EMAIL_REGEX.match(user_email)):
            raise Exception()
        user = db.session.query(User).filter_by(user_email=user_email, user_type='s').first()
        if not user:
            create_new_user(user_email, user_password, json)
            db.session.commit()
            return Response(status=200)
        else:
            return Response(status=409)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/log_in', methods=['POST'])
def log_in():
    print(request.headers)
    print(request.data)
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
    print(request.headers)
    print(request.data)
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
        return Response(status=404)


@app.route('/subscribe_email', methods=['POST'])
def subscribe_email():
    print(request.headers)
    print(request.data)
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
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/unsubscribe_email', methods=['POST'])
def unsubscribe_email():
    print(request.headers)
    print(request.data)
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
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/privacy_settings', methods=['POST'])
def get_privacy_settings():
    print(request.headers)
    print(request.data)
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
                             "profile_is_visible": privacy_settings.profile_visible,
                             "duels_exceptions": exceptions_names})
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/privacy_duels_exceptions', methods=['POST'])
def get_privacy_duels_exceptions_list():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']

        per_page = int(request.args.get("per_page"))
        page_number = int(request.args.get("page_number"))
        if check_token(user_id, token):

            friends = db.session.query(UserData.user_id, UserData.user_name, UserData.avatar_link) \
                .group_by(Friendship.user_id, Friendship.friend_id) \
                .outerjoin(Friendship,
                           db.or_(Friendship.user_id == UserData.user_id, Friendship.friend_id == UserData.user_id)) \
                .filter(db.or_(Friendship.user_id == user_id, Friendship.friend_id == user_id)) \
                .filter(UserData.user_id != user_id) \
                .order_by(db.asc(UserData.user_name)) \
                .paginate(page_number, per_page, False).items

            if len(friends) == 0:
                return json_200([])

            friends = [dict(zip(["user_id", "user_name", "avatar_link"], friend)) for friend in
                       friends]

            for friend in friends:
                is_exception = db.session.query(PrivacyDuelsException).filter_by(user_id=int(user_id),
                                                                                 exception_id=friend[
                                                                                     'user_id']).scalar() is not None if user_id else False
                friend.update({'is_exception': is_exception})

            return json_200(friends)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/notifications', methods=['POST'])
def get_notifications():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']

        per_page = int(request.args.get("per_page"))
        page_number = int(request.args.get("page_number"))
        if check_token(user_id, token):

            db.session.query(UserData).filter_by(user_id=user_id).update(dict(notifications_are_checked=True))
            db.session.commit()

            notifications = db.session.query(UserData.user_id,
                                             UserData.user_name,
                                             UserData.avatar_link,
                                             Notification.notification_type,
                                             Notification.datetime_sent) \
                .filter(UserData.user_id == Notification.id_user_from) \
                .filter(Notification.user_id == user_id).order_by(db.desc(Notification.datetime_sent)).paginate(
                page_number, per_page, False).items

            notifications_dicts = [dict(zip(["user_id", "user_name", "avatar_link", "notification_type"], notification))
                                   for
                                   notification in
                                   notifications]

            for idx, notification in enumerate(notifications):
                time_diff = datetime.utcnow() - notification.datetime_sent
                is_my_friend = db.session.query(Friendship).filter(
                    db.or_(db.and_(Friendship.user_id == int(user_id),
                                   Friendship.friend_id == notifications_dicts[idx]['user_id']),
                           db.and_(Friendship.user_id == notifications_dicts[idx]['user_id'],
                                   Friendship.friend_id == int(
                                       user_id)))).scalar() is not None if user_id is not None else False

                friendship_request = db.session.query(FriendshipRequest).filter(
                    db.or_(db.and_(FriendshipRequest.requesting_id == int(user_id),
                                   FriendshipRequest.recipient_id == notifications_dicts[idx]['user_id']),
                           db.and_(FriendshipRequest.requesting_id == notifications_dicts[idx]['user_id'],
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

                notifications_dicts[idx].update(is_my_friend)
                notifications_dicts[idx].update({"seconds_ago": int(time_diff.total_seconds())})

            return json_200(notifications_dicts)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/edit_duels_exceptions', methods=['POST'])
def edit_duels_exceptions():
    print(request.headers)
    print(request.data)
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
                                                                                      'exception_id']).one()
                    db.session.delete(exception)
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
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/edit_privacy_settings', methods=['POST'])
def edit_privacy_settings():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            privacy_settings = db.session.query(PrivacySettings).filter_by(user_id=user_id).one()

            if 'duels_invites_from' in json['privacy_settings']:
                privacy_settings.duels_invites_from = json['privacy_settings']['duels_invites_from']
            if 'show_in_ratings' in json['privacy_settings']:
                privacy_settings.show_in_ratings = json['privacy_settings']['show_in_ratings']
            if 'profile_is_visible' in json['privacy_settings']:
                privacy_settings.profile_visible = json['privacy_settings']['profile_is_visible']

            db.session.commit()
            return Response(status=200)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/send_friendship', methods=['POST'])
def send_friendship():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):

            if db.session.query(FriendshipRequest).filter(
                    db.or_(db.and_(FriendshipRequest.requesting_id == user_id,
                                   FriendshipRequest.recipient_id == json['friend_id']),
                           db.and_(FriendshipRequest.requesting_id == json['friend_id'],
                                   FriendshipRequest.recipient_id == user_id))).scalar() is None:
                friendship_request = FriendshipRequest(requesting_id=user_id, recipient_id=json['friend_id'])
                notification = Notification(user_id=json['friend_id'], id_user_from=user_id, notification_type='f',
                                            datetime_sent=datetime.utcnow())

                user_data = db.session.query(UserData).filter_by(user_id=int(user_id)).first()
                firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=json['friend_id']).all()
                db.session.query(UserData).filter_by(user_id=json['friend_id']).update(
                    dict(notifications_are_checked=False))

                last_friend_notification = db.session.query(Notification).filter_by(user_id=user_id,
                                                                                    id_user_from=json['friend_id'],
                                                                                    notification_type="f").order_by(
                    db.desc(Notification.datetime_sent)).first()

                hour_from_last_friend_request = (last_friend_notification is None) or (
                        divmod((notification.datetime_sent - last_friend_notification.datetime_sent).seconds, 3600)[
                            0] >= 1)

                if hour_from_last_friend_request:

                    for token_data in firebase_tokens:
                        content = {'type': 'f', 'user_name': user_data.user_name, 'user_id': str(user_id)}

                        if user_data.avatar_link:
                            content.update({'avatar_link': user_data.avatar_link})

                        try:
                            message = messaging.Message(data=content,
                                                        token=token_data.token)
                            messaging.send(message)
                        except Exception as e:
                            db.session.delete(token_data)

                    db.session.add(notification)
                db.session.add(friendship_request)
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=404)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/accept_friendship', methods=['POST'])
def accept_friendship():
    print(request.headers)
    print(request.data)
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
                            FriendshipRequest.recipient_id == int(user_id)))).first()

                if friendship_request:
                    notification = Notification(user_id=json['friend_id'], id_user_from=user_id, notification_type='a',
                                                datetime_sent=datetime.utcnow())

                    user_data = db.session.query(UserData).filter_by(user_id=int(user_id)).first()
                    firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=json['friend_id']).all()
                    db.session.query(UserData).filter_by(user_id=json['friend_id']).update(
                        dict(notifications_are_checked=False))

                    for token_data in firebase_tokens:
                        content = {'type': 'a', 'user_name': user_data.user_name, 'user_id': str(user_id)}

                        if user_data.avatar_link:
                            content.update({'avatar_link': user_data.avatar_link})

                        try:
                            message = messaging.Message(data=content,
                                                        token=token_data.token)
                            messaging.send(message)
                        except Exception as e:
                            db.session.delete(token_data)

                    db.session.delete(friendship_request)
                    db.session.add(friendship)
                    db.session.add(notification)
                    db.session.commit()
                    return Response(status=200)
                else:
                    return Response(status=404)
            else:
                return Response(status=404)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/reject_friendship', methods=['POST'])
def reject_friendship():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            friendship_request = db.session.query(FriendshipRequest).filter(db.or_(
                db.and_(FriendshipRequest.requesting_id == int(user_id),
                        FriendshipRequest.recipient_id == json['friend_id']),
                db.and_(FriendshipRequest.requesting_id == json['friend_id'],
                        FriendshipRequest.recipient_id == int(user_id)))).first()

            if friendship_request:
                db.session.delete(friendship_request)
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=404)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['auth_data']['user_id']
        token = json['auth_data']['user_token']
        if check_token(user_id, token):
            friend = db.session.query(Friendship).filter(
                db.or_(db.and_(Friendship.user_id == int(user_id), Friendship.friend_id == json['friend_id']),
                       db.and_(Friendship.user_id == json['friend_id'], Friendship.friend_id == int(user_id)))).first()
            duels_exception = db.session.query(PrivacyDuelsException).filter_by(user_id=int(user_id),
                                                                                exception_id=json['friend_id']).first()
            if friend:
                if duels_exception:
                    db.session.delete(duels_exception)
                db.session.delete(friend)
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=404)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/cancel_friendship', methods=['POST'])
def cancel_friendship():
    print(request.headers)
    print(request.data)
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
                            FriendshipRequest.recipient_id == int(user_id)))).first()

            if friendship_request:
                db.session.delete(friendship_request)
                db.session.commit()
                return Response(status=200)
            else:
                return Response(status=404)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/authentication', methods=['POST'])
def check_correct_token():
    print(request.headers)
    print(request.data)
    try:
        json = request.get_json()
        user_id = json['user_id']
        token = json['user_token']
        return Response(str(check_token(user_id, token) is not None).lower(), status=200)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/has_friends', methods=['GET'])
def has_friends():
    print(request.headers)
    print(request.data)
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
    print(request.headers)
    print(request.data)
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
                .filter(db.or_(Friendship.user_id == int(friend_of_user_id if friend_of_user_id else user_id), Friendship.friend_id == int(friend_of_user_id if friend_of_user_id else user_id)))\
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
                        friends_query = friends_query.filter(db.or_(UserData.user_name.ilike(user_name + '%'), UserData.user_full_name.ilike(user_name + '%')))

            if friends_sort is not None:
                friends_query = friends_query.order_by(friends_sort)

            users = friends_query.paginate(page_number, per_page, False).items

        else:

            friends_ids_subquery = db.session.query(UserData.user_id) \
                .outerjoin(Friendship,
                           db.or_(Friendship.user_id == UserData.user_id, Friendship.friend_id == UserData.user_id)) \
                .filter(db.or_(Friendship.user_id == int(user_id), Friendship.friend_id == int(user_id)))\
                .filter(UserData.user_id != int(user_id))\
                .subquery()

            users_query = db.session.query(UserData.user_id, UserData.user_name, UserData.avatar_link) \
                .filter(UserData.user_id.notin_(friends_ids_subquery))

            if starts_with:
                user_name = starts_with.replace('@', '')
                users_query = users_query.filter(
                    db.or_(UserData.user_name.ilike(user_name + '%'), UserData.user_full_name.ilike(user_name + '%')))

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
            db.session.query(UserData).filter_by(user_id=145).update(
                dict(notifications_are_checked=True))
            db.session.commit()
            return Response(status=200)
        else:
            return Response(status=404)
    except Exception as e:
        print(e)
        return Response(status=400)


@app.route('/is_my_friend', methods=['GET'])
def check_is_my_friend():
    print(request.headers)
    print(request.data)
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

        print(response)
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
    operators = ['-', '+', '/', '*']
    for operator in operators:
        if eval(components[0] + operator + components[1]) == int(result):
            return operator


def inverse_number_operator(number):
    if '-' in number:
        return number.replace('-', '+')
    else:
        return '-' + number


def solve_x(equation):
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


def create_new_user(user_email, user_password, unregistered_user_data_json):
    hash_password = encrypt(user_password) if user_password else None
    new_user = User(user_email=user_email, user_type='s' if hash_password else 'g', datetime_added=datetime.utcnow(),
                    user_password=hash_password)
    db.session.add(new_user)
    db.session.commit()

    name = user_email.split('@')[0]
    if "user_data" in unregistered_user_data_json:
        user_data = UserData(user_id=new_user.user_id, user_public_id=uuid.uuid1(), user_name=name,
                             current_level=unregistered_user_data_json["user_data"]["current_level"],
                             current_level_XP=unregistered_user_data_json["user_data"]["current_level_XP"],
                             streak_days=unregistered_user_data_json["user_data"]["streak_days"],
                             streak_datetime=convert_datetime_str(
                                 unregistered_user_data_json["user_data"]["streak_datetime"]),
                             completed_parts=unregistered_user_data_json["user_data"]["completed_parts"])
    else:
        user_data = UserData(user_id=new_user.user_id, user_public_id=uuid.uuid1(), user_name=name)
    db.session.add(user_data)

    if "user_statistics" in unregistered_user_data_json:
        for stat in unregistered_user_data_json['user_statistics']:
            stat.update({'user_id': new_user.user_id})
            user_stat = UserStatistics(**stat)
            user_stat.datetime = convert_datetime_str(user_stat.datetime)
            db.session.add(user_stat)

    privacy_settings = PrivacySettings(user_id=new_user.user_id)
    db.session.add(privacy_settings)

    thread = threading.Thread(target=send_mail.send_mail, args=(user_email,))
    thread.start()
    return user_data


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
    new_token = UserToken(user_id=user_id, user_token=token, device_id=device_id)

    db.session.add(new_token)
    return token


def get_offline_exercises_list(exercises, offline_exercises_diff):
    offline_exercises = copy.deepcopy(exercises)
    for idx, chapter_part in enumerate(offline_exercises):
        for idx1, exercise in enumerate(chapter_part['exercises']):
            if exercise['type'] == 'exercise':
                replace_item = [d for d in offline_exercises_diff if
                                d['exercise_number'] == exercise['exercise_number']]
                if len(replace_item) > 0:
                    exercise = replace_item[0]

                if exercise.get('exercise_number', None):
                    if exercise['exercise_type'] == 1:
                        exercise['answer'] = exercise['exercise_info']['title']
                    elif exercise['exercise_type'] == 2 or exercise['exercise_type'] == 3 or exercise['exercise_type'] == 4:
                        exercise['answer'] = exercise['exercise_info']['title'][1]
                    elif exercise['exercise_type'] == 5:
                        title_number = int(exercise['exercise_info']['title'].split(' ')[0])
                        for variant in exercise['exercise_info']['variants']:
                            if eval(variant) == title_number:
                                exercise['answer'] = variant
                    elif exercise['exercise_type'] == 6:
                        exercise['answer'] = str(eval(exercise['exercise_info']['title'].split('=')[0]))
                    elif exercise['exercise_type'] == 7:
                        equation_parts = exercise['exercise_info']['title'].split('=')
                        equation_result = eval(equation_parts[0]) == eval(equation_parts[1])
                        exercise['answer'] = str(equation_result).lower()
                    elif exercise['exercise_type'] == 8:
                        parts = exercise['exercise_info']['title'].replace('...', 'x').replace(' ', '').split('=')
                        result = solve_x(parts[0] + inverse_number_operator(parts[1]))
                        exercise['answer'] = str(result)
                    elif exercise['exercise_type'] == 10:
                        result = solve_x(
                            exercise['exercise_info']['title_parts'][0] + 'x' + inverse_number_operator(
                                exercise['exercise_info']['title_parts'][1].replace('=', '')))
                        exercise['answer'] = str(result)
                    elif exercise['exercise_type'] == 11:
                        int_parts = list(map(int, exercise['exercise_info']['title_parts']))
                        compare_to_number = int(exercise['exercise_info']['compare_number'])
                        filter = exercise['exercise_info']['filter']
                        if filter == "bigger":
                            result = [x > compare_to_number for x in int_parts]
                        elif "lower":
                            result = [x < compare_to_number for x in int_parts]
                        result = result.count(True)
                        exercise['answer'] = str(result)
                    elif exercise['exercise_type'] == 12:
                        parts = exercise['exercise_info']['title'].replace('...', 'x').replace(' ', '').split('=')
                        for variant in exercise['exercise_info']['variants']:
                            result = eval(parts[0].replace('x', variant))
                            if result == int(parts[1]):
                                exercise['answer'] = variant
                    elif exercise['exercise_type'] == 13:
                        exercise['answer'] = str(eval(exercise['exercise_info']['title'][1]))
                    elif exercise['exercise_type'] == 14:
                        title_number = int(exercise['exercise_info']['title'][1])
                        for variant in exercise['exercise_info']['variants']:
                            if eval(variant) == title_number:
                                exercise['answer'] = variant
                    elif exercise['exercise_type'] == 15:
                        title_number = int(exercise['exercise_info']['title'])
                        true_answers = []
                        for variant in exercise['exercise_info']['variants']:
                            if eval(variant) == title_number:
                                true_answers.append(variant)
                        exercise['answer'] = ','.join(true_answers)
                    elif exercise['exercise_type'] == 16:
                        equation_parts = [exercise['exercise_info']['title_parts'][0], exercise['exercise_info']['title_parts'][1].split('=')[0]]
                        equation_result = exercise['exercise_info']['title_parts'][1].split('=')[1]
                        exercise['answer'] = calc_operators(equation_parts, equation_result)
                    elif exercise['exercise_type'] == 17:
                        equation_result = str(eval(exercise['exercise_info']['title'][1]))
                        exercise['answer'] = equation_result
                offline_exercises[idx]['exercises'][idx1] = exercise
    return offline_exercises


CORS(app)


def run():
    app.run(host="0.0.0.0", port=5037)


offline_exercises = get_offline_exercises_list(exercises, offline_exercises_diff)

run()
