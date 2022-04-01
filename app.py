import datetime
import html.parser
import os
import shutil
import subprocess
import traceback
import uuid

import flask
import yaml
from flask import Flask, make_response, jsonify
from flask import request

app = Flask(__name__)

BLOG_CACHE_PATH = os.getenv('BLOG_CACHE_PATH', 'blog_cache')
BLOG_GIT_SSH = os.getenv('BLOG_GIT_SSH', 'git@gitee.com:RainbowYYQ/my-blog.git')
POSTS_PATH = os.getenv('POSTS_PATH', os.path.join(BLOG_CACHE_PATH, 'content', 'posts'))
BLOG_BRANCH = os.getenv('BLOG_BRANCH', 'master')
NEW_BLOG_TEMPLATE_PATH = os.getenv('NEW_BLOG_TEMPLATE_PATH', os.path.join(BLOG_CACHE_PATH, 'archetypes', 'posts.md'))
STATIC_FILES = {}

IS_INIT_WORKSPACE = False


def delete_image_not_included(specific_post=None):
    # 删除已经上传但是文章里没引用到的图片
    def scan_post(dir_name):
        cur_post_content = ""
        md_file = os.path.join(POSTS_PATH, dir_name, 'index.md')
        if os.path.isfile(md_file):
            with open(md_file, mode='r', encoding='utf-8') as f:
                cur_post_content = f.read()
        for file in os.listdir(os.path.join(POSTS_PATH, dir_name)):
            if file == 'index.md':
                continue
            if file not in cur_post_content:
                delete_file_path = os.path.join(POSTS_PATH, dir_name, file)
                app.logger.info('file not used %s delete it.', delete_file_path)
                os.remove(delete_file_path)

    if specific_post:
        scan_post(specific_post)
    else:
        for dir_name in os.listdir(POSTS_PATH):
            scan_post(dir_name)


def cache_static_files():
    global STATIC_FILES
    STATIC_FILES.clear()
    for root, dirs, files in os.walk(POSTS_PATH, topdown=False):
        for name in files:
            if name == 'index.md':
                continue
            if name in STATIC_FILES:
                raise Exception('static file ' + name + " duplicated: " + root + " " + STATIC_FILES[name])
            STATIC_FILES[name] = root


@app.route('/<file_name>', methods=['GET'])
def get_file(file_name):
    if file_name in STATIC_FILES:
        return make_response(flask.send_from_directory(STATIC_FILES[file_name], file_name))
    else:
        return flask.Response(status=404)


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
    return yaml.load('\n'.join(yaml_lines), Loader=yaml.BaseLoader)


@app.route('/api/posts/changes', methods=['GET'])
def get_post_changes():
    delete_image_not_included()
    git_add()
    status_result_for_show = pretty_git_status(git_status())
    return make_response(jsonify(status_result_for_show))


def pretty_git_status(status_result):
    def _get_title(filepath):
        return get_md_yaml(os.path.join(BLOG_CACHE_PATH, filepath)).get('title') if status.endswith(
            "index.md") else ''

    status_result_for_show = []
    for status in status_result:
        flag, filepath = status.split()
        if status.startswith("M "):
            status_result_for_show.append("修改 " + _get_title(filepath) + " " + filepath)
        elif status.startswith("A "):
            status_result_for_show.append("新增 " + _get_title(filepath) + " " + filepath)
        elif status.startswith("D "):
            status_result_for_show.append("删除 " + filepath)
        else:
            status_result_for_show.append(status)
    return status_result_for_show


def git_status():
    output = subprocess.run(f'git status -s', cwd=BLOG_CACHE_PATH, capture_output=True, check=True)
    return [line.strip() for line in output.stdout.decode('utf-8').splitlines()]


@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts = {}
    for i in os.listdir(POSTS_PATH):
        post_yaml = get_md_yaml(os.path.join(POSTS_PATH, i, 'index.md'))
        posts[i] = {
            'dirName': i,
            'title': post_yaml['title'] if yaml else i
        }
    return make_response(jsonify(posts))


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


@app.route('/api/post/<filename>', methods=['GET'])
def get_post(filename):
    md_path = os.path.join(POSTS_PATH, filename, 'index.md')
    if os.path.isfile(md_path):
        return make_response(flask.send_file(md_path))
    return flask.Response(status=404)


@app.route('/api/post/<filename>', methods=['DELETE'])
def delete_post(filename):
    shutil.rmtree(os.path.join(POSTS_PATH, filename), ignore_errors=True)
    git_add()
    return flask.Response(status=200)


@app.route('/api/post/<filename>', methods=['POST'])
def save_post(filename):
    post = html.unescape(request.stream.read().decode('utf-8'))
    if not os.path.exists(os.path.join(POSTS_PATH, filename)):
        return flask.Response(status=404)
    with open(os.path.join(POSTS_PATH, filename, 'index.md'), mode='w', encoding='utf-8') as f:
        f.write(post)
    return flask.Response(status=200)


@app.route('/', methods=['GET'])
def home():
    return make_response(flask.send_file("index.html"))


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return flask.Response(status=404)


@app.route('/api/reset', methods=['POST'])
def reset():
    check_initializing()
    if os.path.exists(BLOG_CACHE_PATH):
        backup_path = BLOG_CACHE_PATH + "_backup"
        shutil.rmtree(backup_path, ignore_errors=True)
        shutil.copytree(BLOG_CACHE_PATH, backup_path, dirs_exist_ok=True)
    init_git()
    return flask.Response(status=200)


@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_files():
    success_files = {}
    failed_files = []
    for file in request.files.getlist('files'):
        try:
            suffix = os.path.splitext(file.filename)[1]
            new_filename = f"{str(uuid.uuid4()).replace('-', '')}{suffix}"
            dir_name = request.form.get('belongDirName')
            if not dir_name:
                raise Exception('belongDirName is empty')
            file.save(os.path.join(POSTS_PATH, dir_name, new_filename))
            success_files[file.filename] = f'{new_filename}'
        except Exception:
            traceback.print_exc()
            failed_files.append(file.filename)
    git_add()
    cache_static_files()
    ret_dict = {
        "msg": "",
        "code": 0,
        "data": {
            "errFiles": failed_files,
            "succMap": success_files
        }
    }
    response = make_response(jsonify(ret_dict))
    return response


def git_add():
    subprocess.run(f'git add -A', cwd=BLOG_CACHE_PATH, capture_output=True, check=True)


def init_git():
    global IS_INIT_WORKSPACE
    if IS_INIT_WORKSPACE:
        return
    IS_INIT_WORKSPACE = True
    try:
        if os.path.exists(BLOG_CACHE_PATH):
            shutil.rmtree(BLOG_CACHE_PATH, ignore_errors=False)
        os.makedirs(BLOG_CACHE_PATH, exist_ok=True)
        subprocess.run(f'git clone {BLOG_GIT_SSH} -b {BLOG_BRANCH} {BLOG_CACHE_PATH}')
        cache_static_files()
    finally:
        IS_INIT_WORKSPACE = False


def check_initializing():
    if IS_INIT_WORKSPACE:
        raise Exception('workspace is in initializing')


if __name__ == '__main__':
    if not os.path.exists(BLOG_CACHE_PATH):
        init_git()
    cache_static_files()
    app.run()
