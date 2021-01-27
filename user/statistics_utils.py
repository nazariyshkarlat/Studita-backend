from database.models import UserStatistics, as_dict

labels = ["obtained_XP", "time_spent", "completed_exercises", "completed_trainings", "obtained_achievements",
          "completed_chapters", "max_streak_days"]


def get_all_time_user_statistics(user_id, db):

    results = db.session.query(db.func.coalesce(db.func.sum(UserStatistics.obtained_XP), 0),
                             db.func.coalesce(db.func.sum(UserStatistics.time_spent), 0),
                             db.func.coalesce(db.func.sum(UserStatistics.completed_exercises), 0),
                             db.func.coalesce(db.func.sum(UserStatistics.completed_trainings), 0),
                             db.func.coalesce(db.func.sum(UserStatistics.obtained_achievements), 0),
                             db.func.coalesce(db.func.sum(UserStatistics.completed_chapters), 0),
                             db.func.coalesce(db.func.max(UserStatistics.days_streak), 0)) \
        .filter_by(user_id=user_id)[0]

    int_results = (int(result) for result in results)

    return dict(zip(labels, int_results))