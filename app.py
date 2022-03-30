import datetime
import html.parser
import os.path
import shutil
import subprocess
import traceback
import uuid

import flask
import yaml
from flask import Flask, make_response, jsonify
from flask import request

app = Flask(__name__)
BLOG_CACHE_PATH = 'blog_cache'
BLOG_GIT_SSH = 'git@gitee.com:RainbowYYQ/my-blog.git'
POSTS_PATH = os.path.join(BLOG_CACHE_PATH, 'content', 'posts')

current_post_dir_name = '20220330122938'
current_post_path = os.path.join(POSTS_PATH, current_post_dir_name)


@app.route('/<file_name>', methods=['GET'])
def get_file(file_name):
    return make_response(flask.send_from_directory(current_post_path, file_name))


def get_md_yaml(file_path):
    yaml_lines = []
    if not os.path.isfile(file_path):
        return {}
    with open(file_path, mode='r', encoding='utf-8') as f:
        start_flag = False
        for line in f:
            if start_flag and not line.startswith('---'):
                yaml_lines.append(line)
            if line.startswith('---'):
                if start_flag:
                    break
                else:
                    start_flag = True
    return yaml.load('\n'.join(yaml_lines))


@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts = {}
    for i in os.listdir(POSTS_PATH):
        yaml = get_md_yaml(os.path.join(POSTS_PATH, i, 'index.md'))
        posts[i] = {
            'dirName': i,
            'title': yaml['title'] if yaml else i,
            'isEditing': False
        }
    return make_response(jsonify(posts))


def switch_edit_post(target):
    global current_post_path, current_post_dir_name
    current_post_path = os.path.join(POSTS_PATH, target)
    current_post_dir_name = target


def read_post_template():
    with open(os.path.join(BLOG_CACHE_PATH, 'archetypes', 'posts.md'), mode='r', encoding='utf-8') as f:
        return f.read()


@app.route('/api/post/create', methods=['POST'])
def create_post():
    now = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=+8)))
    post_dir_name = now.strftime('%Y%m%d%H%M%S')
    os.mkdir(os.path.join(POSTS_PATH, post_dir_name))
    template = read_post_template()
    template = template.replace('{{title}}', post_dir_name)
    template = template.replace('{{date}}', now.isoformat())
    template = template.replace('{{categories}}', '[]')
    with open(os.path.join(POSTS_PATH, post_dir_name, 'index.md'), mode='w', encoding='utf-8') as f:
        f.write(template)
    return make_response(jsonify({'dirName': post_dir_name}))


@app.route('/api/post/startEdit/<filename>', methods=['POST'])
def start_edit_post(filename):
    md_path = os.path.join(POSTS_PATH, filename, 'index.md')
    if os.path.isfile(md_path):
        switch_edit_post(filename)
        return make_response(flask.send_file(md_path))
    return flask.Response(status=404)


@app.route('/api/post/endEdit/<filename>', methods=['POST'])
def end_edit_post(filename):
    post = request.stream.read().decode('utf-8')
    post=html.unescape(post)
    with open(os.path.join(POSTS_PATH, filename, 'index.md'), mode='w', encoding='utf-8') as f:
        f.write(post)
    return flask.Response(status=200)


@app.route('/', methods=['GET'])
def home():
    return make_response(flask.send_file("index.html"))


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return flask.Response(status=404)


@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_files():
    success_files = {}
    failed_files = []
    for file in request.files.getlist('files'):
        try:
            suffix = os.path.splitext(file.filename)[1]
            new_filename = f"{str(uuid.uuid4()).replace('-', '')}{suffix}"
            file.save(os.path.join(current_post_path, new_filename))
            success_files[file.filename] = f'{new_filename}'
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


def init_git():
    shutil.rmtree(BLOG_CACHE_PATH, ignore_errors=True)
    os.mkdir(BLOG_CACHE_PATH)
    subprocess.run(f'git clone {BLOG_GIT_SSH} -b master {BLOG_CACHE_PATH}')


if __name__ == '__main__':
    # init_git()
    app.run()
