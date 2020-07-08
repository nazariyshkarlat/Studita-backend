from database.models import UserData


def is_valid_edit_profile_data(user_name, user_full_name):
    return (len(user_name) in range_include(4, 25)) and ((user_full_name is None) or (len(user_full_name) in range_include(2, 30)))


def user_name_not_exists(db, user_name, current_user_name):
    return ((current_user_name == user_name) or (
        not db.session.query(UserData).filter_by(user_name=user_name).scalar()))


def range_include(start, end):
    return range(start, end+1)