from database.models import UserData
import re

MIN_USER_NAME_LENGTH = 3
MAX_USER_NAME_LENGTH = 25
MIN_NAME_LENGTH = 0
MIN_BIO_LENGTH = 0
MAX_BIO_LENGTH = 150
MAX_NAME_LENGTH = 30

def is_valid_profile_data(user_name, name, bio):
    return match_user_name(user_name) and match_name(name) and match_bio(bio)


def user_name_not_exists(db, user_name, current_user_name):
    return ((current_user_name == user_name) or (
        not db.session.query(UserData).filter_by(user_name=user_name).scalar()))


def range_include(start, end):
    return range(start, end + 1)


def match_name(name):
    return (name is None) or (len(name) in range_include(MIN_NAME_LENGTH, MAX_NAME_LENGTH))


def match_bio(bio):
    return (bio is None) or (len(bio) in range_include(MIN_BIO_LENGTH, MAX_BIO_LENGTH))


def match_user_name(strg, search=re.compile(r'[^A-Za-z0-9_.]').search, search_exc=re.compile(r"\.{2,}").search):
    return not bool(search(strg)) and (len(strg) in range_include(MIN_USER_NAME_LENGTH, MAX_USER_NAME_LENGTH)) and not (strg.startswith('.') or strg.endswith('.')) and (not search_exc(strg)) and any(x.isalpha() for x in strg)