from user.achievements.achievements_info import *
import user.statistics_utils as statistics_utils
import user.level_utils as level_utils
from datetime import datetime
from database.models import UserStatistics, Achievement, UserData, Notification, FirebaseToken,  as_dict_array
import firebase_admin.messaging as messaging


def giveNewImprovableAchievements(user_id, db):
    db_achievements = as_dict_array(db.session.query(Achievement).filter_by(user_id=user_id).all())
    stat = statistics_utils.get_all_time_user_statistics(user_id, db)
    user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
    giveImprovableAchievementByType(user_data, TYPE_STREAK, user_id, stat["max_streak_days"], db_achievements, db)
    giveImprovableAchievementByType(user_data, TYPE_EXERCISES, user_id, stat["completed_exercises"], db_achievements, db)
    giveImprovableAchievementByType(user_data, TYPE_TRAININGS, user_id, stat["completed_trainings"], db_achievements, db)
    giveImprovableAchievementByType(user_data, TYPE_CHAPTERS, user_id, stat["completed_chapters"], db_achievements, db)

    db.session.commit()


def giveImprovableAchievementByType(user_data, achievement_type, user_id, statistics_value, db_achievements, db):
    current_achievement_level = NO_LEVEL if not any(achievement["type"] == achievement_type for achievement in db_achievements) \
        else next(achievement  for achievement in db_achievements if(achievement["type"] == achievement_type))["level"]

    given_level = 0
    obtained_XP = 0
    achievement_info = next(achievement_info for achievement_info in achievements_info if achievement_info["type"] == achievement_type)
    for idx, progress in enumerate(achievement_info["progress"]):
        if statistics_value >= progress and idx+1 > current_achievement_level:
            given_level = idx+1
            obtained_XP = obtained_XP + achievement_info["XP_rewards"][idx]
            sendAchievementNotification(user_id, db, achievement_type, given_level)

    if given_level > 0:
        db.session.add(Achievement(user_id = user_id, type = achievement_type, level = given_level))
    if obtained_XP > 0:
        new_levels_count = level_utils.get_new_levels_count(user_data, obtained_XP)
        new_level_XP = level_utils.get_new_level_XP(user_data, obtained_XP)
        user_data.current_level = user_data.current_level + new_levels_count
        user_data.current_level_XP = new_level_XP


def giveNonImprovableAchievementByType(achievement_type, user_id, db):
    db.session.add(Achievement(user_id = user_id, type = achievement_type, level = 1))
    obtained_XP = next(achievement_info for achievement_info in achievements_info if achievement_info["type"] == achievement_type)["XP_reward"]
    user_data = db.session.query(UserData).filter_by(user_id=user_id).one()
    new_levels_count = level_utils.get_new_levels_count(user_data, obtained_XP)
    new_level_XP = level_utils.get_new_level_XP(user_data, obtained_XP)
    user_data.current_level = user_data.current_level + new_levels_count
    user_data.current_level_XP = new_level_XP

    sendAchievementNotification(user_id, db, achievement_type, 1)
    db.session.commit()


def sendAchievementNotification(user_id, db, achievement_type, achievement_level):
    type_text = 'ach_t{0}_l{1}'.format(achievement_type, achievement_level)

    content = formNotificationDict(user_id, achievement_type, achievement_level)
    notification = Notification(user_id=user_id, notification_type=type_text,
                                datetime_sent=datetime.utcnow())
    db.session.add(notification)

    firebase_tokens = db.session.query(FirebaseToken).filter_by(user_id=user_id).all()
    db.session.query(UserData).filter_by(user_id=user_id).update(
        dict(notifications_are_checked=False))

    for token_data in firebase_tokens:
        try:
            message = messaging.Message(data=content,
                                        token=token_data.token)
            messaging.send(message)
        except Exception as e:
            db.session.delete(token_data)


def formNotificationDict(user_id, achievement_type, achievement_level):
    achievement_data = next(
        achievement_data for achievement_data in achievements if achievement_data["type"] == achievement_type)
    achievement_info = next(
        achievement_info for achievement_info in achievements_info if achievement_info["type"] == achievement_type)

    type_text = 'ach_t{0}_l{1}'.format(achievement_type, achievement_level)

    isImprovable = "progress" in achievement_info

    if (not isImprovable) or (isImprovable and achievement_level == LEVEL_BRONZE):
        title = notifications_text_russian[0].format(achievement_data['title'])
    else:
        title = notifications_text_russian[1].format(achievement_data['title'])

    print(achievement_type)
    print(isImprovable)
    if not isImprovable:
        subtitle = notifications_text_russian[2].format(achievement_info['XP_reward'])
    else:
        subtitle = notifications_text_russian[3][achievement_level - 1].format(achievement_info['XP_rewards'][achievement_level-1])

    if not isImprovable:
        icon_url = achievement_data['icon_url']
    else:
        icon_url = achievement_data['icon_url'][achievement_level - 1]

    return {'type': type_text,
                   'title': title,
                   'subtitle': subtitle,
                   'user_id': str(user_id),
                   'image_url': icon_url
            }


def getAchievementProgressByType(achievement_type, user_id, db):
    stat = statistics_utils.get_all_time_user_statistics(user_id, db)

    if achievement_type == TYPE_STREAK:
        return stat["max_streak_days"]
    elif achievement_type == TYPE_EXERCISES:
        return stat["completed_exercises"]
    elif achievement_type == TYPE_TRAININGS:
        return stat["completed_trainings"]
    elif achievement_type == TYPE_CHAPTERS:
        return stat["completed_chapters"]
