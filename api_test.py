import requests
import json

# str = 'curl -H "Content-Type: application/json" -d "{\"user_email\":\"tarasikee3@gmail.com\",\"user_password\":\"232815\"}" -i http://localhost:5037/log_in'

data1 = {"answer": "3"}

port = 5001

r = requests.post(url='http://127.0.0.1:' + str(port) + '/exercises/3', data=json.dumps(data1), headers={'content-type': 'application/json'})

print(r.text)