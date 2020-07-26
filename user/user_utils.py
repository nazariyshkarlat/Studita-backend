from database.models import UserData
import re


def is_valid_edit_profile_data(user_name, user_full_name):
    return match_user_name(user_name) and match_user_full_name(user_full_name) if user_full_name else True


def user_name_not_exists(db, user_name, current_user_name):
    return ((current_user_name == user_name) or (
        not db.session.query(UserData).filter_by(user_name=user_name).scalar()))


def range_include(start, end):
    return range(start, end + 1)


def match_user_name(strg, search=re.compile(r'[^A-Za-z0-9]').search):
    return (not bool(search(strg))) and len(strg) in range_include(4, 25)


def match_user_full_name(strg):
    return all(x.isalpha() or (x.isspace() and strg[idx-1].isalpha()) for idx, x in enumerate(strg)) and (
                (strg is None) or (len(strg) in range_include(2, 30)))