import os.path
import traceback

from flask import Flask, make_response, jsonify
from flask import request

STATIC_PATH = 'static'
app = Flask(__name__, static_url_path='/static', static_folder=STATIC_PATH)


@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_files():
    success_files = {}
    failed_files = []
    for file in request.files.getlist('files'):
        try:
            file.save(os.path.join(STATIC_PATH, file.filename))
            success_files[file.filename] = f'http://127.0.0.1:5000/static/{file.filename}'
        except Exception:
            traceback.print_exc()
            failed_files.append(file.filename)
    ret_dict = {
        "msg": "",
        "code": 0,
        "data": {
            "errFiles": failed_files,
            "succMap": success_files
        }
    }
    response = make_response(jsonify(ret_dict))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


if __name__ == '__main__':
    app.run()
