import requests
import json
import string
import random

# str = 'curl -H "Content-Type: application/json" -d "{\"user_email\":\"tarasikee3@gmail.com\",\"user_password\":\"232815\"}" -i http://localhost:5037/log_in'


def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


for x in range(100, 500):
    add_friend_data = {"auth_data": {"user_id": 145, "user_token": "Ksf!,r?r'bewnEM}%s$yj%0!G?+G0OfBc_2(.-(YDJZb,dXul[>ahK}ka9lq'P%L.Gn-"}, "friend_id": 563+x}
    sign_up_data = {"user_email": get_random_string(8) + "@gmail.com", "user_password": "fwerfASFSADFQWR5232"}

    port = 5000

    r = requests.post(url='http://127.0.0.1:' + str(port) + '/accept_friendship', data=json.dumps(add_friend_data), headers={'content-type': 'application/json'})