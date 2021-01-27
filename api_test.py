import requests
from threading import Thread


# str = 'curl -H "Content-Type: application/json" -d "{\"user_email\":\"tarasikee3@gmail.com\",\"user_password\":\"232815\"}" -i http://localhost:5037/log_in'

def threaded_function():
        r = requests.get(url='https://dl.nure.ua/my/')
        print(r.content)


for x in range(5, 100000):
    thread = Thread(target = threaded_function)
    thread.start()
    thread.join()