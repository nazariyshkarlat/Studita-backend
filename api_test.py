import requests
import json
import string
import random
import time

# str = 'curl -H "Content-Type: application/json" -d "{\"user_email\":\"tarasikee3@gmail.com\",\"user_password\":\"232815\"}" -i http://localhost:5037/log_in'


def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


for x in range(5, 10):
    port = 5000

    r = requests.get(url='http://127.0.0.1:' + str(port) + '/levels', headers={'content-type': 'application/json'})
    time.sleep(2)