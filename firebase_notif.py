import firebase_admin
from firebase_admin import credentials
import firebase_admin.messaging as messaging

cred = credentials.Certificate("serviceAccountKey.json")
default_app = firebase_admin.initialize_app(cred)

message = messaging.Message(data={"title" : "mad", "text": "world"},
                            token="es8BAOchTXyFzyIr9-bqzu:APA91bEleaRXjiWXv42x38LvVeNKlFm0Uox1LOF9_TUehob3Pm37-Yba4-CzX7qEhEHWr9eeRzMkIAehIiMjLgBi32GNGNzf8H_UZbbiDiLm41U8ed9EiPUSVDXbIVU8icM0oEfeN22S")
messaging.send(message)