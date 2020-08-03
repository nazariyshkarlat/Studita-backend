from sqlalchemy import func
from datetime import datetime, timedelta
from database.models import UserStatistics

SEQUENCE_TO_BONUS = 5
SEQUENCE_BONUS = 100
FIRST_LEVEL_XP = 500
TRAINING_XP = 50
NEXT_LEVEL_BONUS = 50
ALL_CORRECT_BONUS = 50
SINGLE_BONUS_EXERCISE_XP = 10
SINGLE_BONUS_TRAINING_XP = 5


def get_next_level(current_level):
    return current_level + 1


def get_level_XP(current_level):
    return FIRST_LEVEL_XP + (current_level - 1) * 100


def percent_to_XP(percent, is_training):
    if percent > 1:
        raise IOError
    return TRAINING_XP if is_training else int(percent * 100)


def get_obtained_XP(user_data, percent, is_training, db, today, exercises_bonus_correct_count):
    return get_obtained_bonus(user_data, percent, is_training, db, today, exercises_bonus_correct_count) + percent_to_XP(percent, is_training)


def get_obtained_bonus(user_data, percent, is_training, db, today, exercises_bonus_correct_count):
    without_level_bonus = (ALL_CORRECT_BONUS if (not is_training and (percent == 1)) else 0) + (SEQUENCE_BONUS if add_sequence_bonus(user_data, is_training, db, today) else 0) + get_exercises_bonus_obtained_XP(is_training, exercises_bonus_correct_count)
    obtained_XP = without_level_bonus + percent_to_XP(percent, is_training)
    return get_new_levels_bonus(user_data, obtained_XP) + without_level_bonus


def get_exercises_bonus_obtained_XP(is_training, correct_answers_count):
    return (correct_answers_count if correct_answers_count <= 15 else 0) * (SINGLE_BONUS_EXERCISE_XP if not is_training else SINGLE_BONUS_TRAINING_XP)


def get_new_levels_count(user_data, obtained_XP):
    new_levels = 0
    level_XP = obtained_XP + user_data.current_level_XP

    max_level_XP = get_level_XP(user_data.current_level + new_levels)

    while level_XP >= max_level_XP:
        level_XP -= max_level_XP
        new_levels += 1
        max_level_XP = get_level_XP(user_data.current_level + new_levels)

    return new_levels


def add_sequence_bonus(user_data, is_training, db, today):
    if not is_training:
        return ((get_today_completed_exercises_count(today, user_data, db)+1) % SEQUENCE_TO_BONUS) == 0
    else:
        return False


def get_today_completed_exercises_count(today, user_data, db):
    today_filter = func.DATE(UserStatistics.datetime) == today
    today_completed = len(db.session.query(UserStatistics)
                          .filter_by(user_id=user_data.user_id)
                          .filter(today_filter)
                          .filter(UserStatistics.obtained_exercises > 0).all())
    return today_completed


def get_new_level_XP(user_data, obtained_XP):
    new_levels = 0
    new_XP_dirty = user_data.current_level_XP + obtained_XP
    new_XP = new_XP_dirty

    max_level_XP = get_level_XP(user_data.current_level + new_levels)

    while new_XP >= max_level_XP:
        new_XP -= max_level_XP
        new_levels += 1
        max_level_XP = get_level_XP(user_data.current_level + new_levels)

    return new_XP


def get_new_levels_bonus(user_data, obtained_XP):
    return get_new_levels_count(user_data, obtained_XP) * NEXT_LEVEL_BONUS
