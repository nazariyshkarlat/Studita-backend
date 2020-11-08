from api import app
from waitress import serve
from paste.translogger import TransLogger

if __name__ == '__main__':
    serve(TransLogger(app), host='0.0.0.0', port=34867, ipv4=True, threads=100)
