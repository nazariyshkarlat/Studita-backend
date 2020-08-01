from database.models import UserData
import re
from collections import Counter


def is_valid_edit_profile_data(user_name):
    return match_user_name(user_name)


def user_name_not_exists(db, user_name, current_user_name):
    return ((current_user_name == user_name) or (
        not db.session.query(UserData).filter_by(user_name=user_name).scalar()))


def range_include(start, end):
    return range(start, end + 1)


def match_user_name(strg, search=re.compile(r'[^A-Za-z0-9_.]').search, search_exc=re.compile(r"\.{2,}").search):
    return not bool(search(strg)) and (len(strg) in range_include(4, 25)) and not (strg.startswith('.') or strg.endswith('.')) and (not search_exc(strg)) and any(x.isalpha() for x in strg)