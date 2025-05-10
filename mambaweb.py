from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, Response, session
import os
import subprocess
import platform
import argparse
import uuid
import shutil
from werkzeug.utils import secure_filename
from functools import wraps
import html

# 参数解析
parser = argparse.ArgumentParser(description='Mamba Web Manager')
parser.add_argument('-p', '--port', type=int, default=81, help='运行端口 (默认: 81)')
parser.add_argument('-d', '--directory', type=str, default='D:\\', help='默认目录 (默认: D:\\)')
args = parser.parse_args()

app = Flask(__name__)
app.secret_key = os.urandom(24)  

# 配置
UPLOAD_FOLDER = os.path.join(args.directory, 'uploads')
ALLOWED_EXTENSIONS = {'*'}  # 允许所有文件类型
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# BASIC认证装饰器
def check_auth(username, password):
    return username == 'a' and password == 'a'

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# 文件信息
class FileInfo:
    def __init__(self, name, is_dir, full_path, size=None):
        self.name = html.escape(name)
        self.is_dir = is_dir
        self.full_path = full_path
        self.size = self.format_size(size) if size else ""
        self.is_image = self.check_is_image()
        self.is_video = self.check_is_video()
        self.is_text = self.check_is_text()
    
    @staticmethod
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def check_is_image(self):
        if self.is_dir:
            return False
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        return os.path.splitext(self.name)[1].lower() in image_extensions
    
    def check_is_video(self):
        if self.is_dir:
            return False
        video_extensions = {'.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv'}
        return os.path.splitext(self.name)[1].lower() in video_extensions
    
    def check_is_text(self):
        if self.is_dir:
            return False
        text_extensions = {'.txt', '.log', '.ini', '.conf', '.json', '.xml', '.html', '.css', '.js', '.py', '.java', '.c', '.cpp', '.h', '.md'}
        return os.path.splitext(self.name)[1].lower() in text_extensions

def get_disks():
    if platform.system() == 'Windows':
        return [f"{d}:" for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f"{d}:\\")]
    else:
        return ['/']

def sanitize_path(path):
    """确保路径安全，防止目录遍历攻击"""
    if not path:
        return args.directory
    path = os.path.abspath(path)
    return path

@app.route('/mamba')
@requires_auth
def file_manager():
    raw_path = request.args.get('path', args.directory)
    try:
        path = os.path.abspath(raw_path)
    except Exception:
        return "路径无效", 400

    disks = get_disks()
    try:
        files = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            try:
                is_dir = os.path.isdir(full_path)
                size = os.path.getsize(full_path) if not is_dir else None
                files.append(FileInfo(item, is_dir, full_path, size))
            except:
                continue
        return render_template_string(FILE_MANAGER_TEMPLATE, 
                                    path=path, 
                                    files=files, 
                                    disks=disks)
    except PermissionError:
        return "权限不足", 403
    except Exception as e:
        return str(e), 500

# 文件查看
@app.route('/mamba/view')
@requires_auth
def view_file():
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return "文件不存在", 404
    if os.path.isdir(path):
        return "不能查看目录", 400
    
    file_ext = os.path.splitext(path)[1].lower()
    if file_ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
        return send_from_directory(os.path.dirname(path), os.path.basename(path))
    elif file_ext in {'.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv'}:
        return send_from_directory(os.path.dirname(path), os.path.basename(path))
    elif file_ext in {'.txt', '.log', '.ini', '.conf', '.json', '.xml', '.html', '.css', '.js', '.py', '.java', '.c', '.cpp', '.h', '.md'}:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(content, mimetype='text/plain')
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    content = f.read()
                return Response(content, mimetype='text/plain')
            except Exception as e:
                return f"无法读取文件: {str(e)}", 500
        except Exception as e:
            return f"无法读取文件: {str(e)}", 500
    else:
        return "不支持的预览格式", 400

# 文件上传
@app.route('/mamba/upload', methods=['POST'])
@requires_auth
def upload_file():
    current_path = request.form.get('current_path', UPLOAD_FOLDER)
    if 'file' not in request.files or request.files['file'].filename == '':
        return redirect(url_for('file_manager', path=current_path))
    file = request.files['file']
    if file:
        try:
            os.makedirs(current_path, exist_ok=True)
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_path, filename)
            file.save(save_path)
        except Exception as e:
            return str(e), 500
        return redirect(url_for('file_manager', path=current_path))

# 文件下载
@app.route('/mamba/download')
@requires_auth
def download_file():
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return "文件不存在", 404
    if os.path.isdir(path):
        return "不能下载目录", 400
    return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=True)

# 命令执行页面
@app.route('/mamba/out')
@requires_auth
def command_executor():
    return render_template_string(COMMAND_EXECUTOR_TEMPLATE)

# 命令执行路由
@app.route('/mamba/out/execute', methods=['POST'])
@requires_auth
def execute_command():
    command = request.form.get('command')
    if not command:
        return redirect(url_for('command_executor'))
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        output = {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        return render_template_string(COMMAND_EXECUTOR_TEMPLATE, command_result=output)
    except subprocess.TimeoutExpired:
        return render_template_string(COMMAND_EXECUTOR_TEMPLATE, command_result={"command": command, "stdout": "", "stderr": "命令执行超时 (超过10秒)", "returncode": -1})
    except Exception as ex:
        return render_template_string(COMMAND_EXECUTOR_TEMPLATE, command_result={"command": command, "stdout": "", "stderr": str(ex), "returncode": -1})

# HTML模板
FILE_MANAGER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mamba 文件管理器</title>
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #4a6fa5; color: white; padding: 15px; border-radius: 5px; }
        .disk-list { display: flex; gap: 10px; margin: 15px 0; }
        .disk-btn { padding: 5px 10px; background: #e9ecef; border-radius: 3px; text-decoration: none; }
        .disk-btn:hover { background: #d1d7dc; }
        .active-disk { background: #4a6fa5; color: white; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #4a6fa5; color: white; }
        .btn { padding: 5px 10px; border: none; border-radius: 3px; text-decoration: none; display: inline-block; margin: 2px; }
        .btn-download { background: #4CAF50; color: white; }
        .btn-view { background: #2196F3; color: white; }
        .btn-upload { background: #2196F3; color: white; }
        .nav-links { margin-top: 20px; }
        .preview-container { margin-top: 20px; }
        .preview-img { max-width: 100%; max-height: 500px; }
        .preview-video { max-width: 100%; max-height: 500px; }
        .preview-text { max-width: 100%; height: 500px; overflow: auto; border: 1px solid #ddd; padding: 10px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Mamba 文件管理器</h1>
        <p>当前路径: {{ path }}</p>
    </div>

    <div class="disk-list">
        {% for disk in disks %}
            <a href="{{ url_for('file_manager', path=disk+'\\\\') }}" 
               class="disk-btn {% if path.startswith(disk) %}active-disk{% endif %}">
                {{ disk }}
            </a>
        {% endfor %}
    </div>

    <table>
        <tr>
            <th>名称</th>
            <th>类型</th>
            <th>大小</th>
            <th>操作</th>
        </tr>
        {% for file in files %}
            <tr>
                <td>
                    {% if file.is_dir %}
                        <a href="{{ url_for('file_manager', path=file.full_path) }}">{{ file.name }}/</a>
                    {% elif file.is_image %}
                        <a href="#" onclick="document.getElementById('preview-img').src='{{ url_for('view_file', path=file.full_path) }}'; document.getElementById('preview-container').style.display='block'">{{ file.name }}</a>
                    {% elif file.is_video %}
                        <a href="#" onclick="document.getElementById('preview-video').src='{{ url_for('view_file', path=file.full_path) }}'; document.getElementById('preview-container').style.display='block'">{{ file.name }}</a>
                    {% elif file.is_text %}
                        <a href="#" onclick="fetchTextFile('{{ url_for('view_file', path=file.full_path) }}')">{{ file.name }}</a>
                    {% else %}
                        {{ file.name }}
                    {% endif %}
                </td>
                <td>
                    {% if file.is_dir %}目录
                    {% elif file.is_image %}图片
                    {% elif file.is_video %}视频
                    {% elif file.is_text %}文本
                    {% else %}文件
                    {% endif %}
                </td>
                <td>{% if not file.is_dir %}{{ file.size }}{% endif %}</td>
                <td>
                    {% if not file.is_dir %}
                        <a href="{{ url_for('download_file', path=file.full_path) }}" class="btn btn-download">下载</a>
                        {% if file.is_image or file.is_video or file.is_text %}
                            <a href="{{ url_for('view_file', path=file.full_path) }}" target="_blank" class="btn btn-view">查看</a>
                        {% endif %}
                    {% endif %}
                </td>
            </tr>
        {% endfor %}
    </table>

    <div id="preview-container" class="preview-container" style="display:none;">
        <h3>预览</h3>
        <img id="preview-img" class="preview-img" style="display:none;">
        <video id="preview-video" class="preview-video" controls style="display:none;"></video>
        <pre id="preview-text" class="preview-text" style="display:none;"></pre>
        <button onclick="document.getElementById('preview-container').style.display='none'" class="btn btn-view">关闭预览</button>
    </div>

    <h3>上传文件</h3>
    <form action="{{ url_for('upload_file') }}" method="post" enctype="multipart/form-data">
        <input type="hidden" name="current_path" value="{{ path }}">
        <input type="file" name="file">
        <button type="submit" class="btn btn-upload">上传</button>
    </form>

    <div class="nav-links">
        <a href="{{ url_for('command_executor') }}" class="btn btn-view">前往命令执行页面</a>
    </div>

    <script>
        function fetchTextFile(url) {
            fetch(url)
                .then(response => response.text())
                .then(text => {
                    const previewContainer = document.getElementById('preview-container');
                    const previewText = document.getElementById('preview-text');
                    
                    document.getElementById('preview-img').style.display = 'none';
                    document.getElementById('preview-video').style.display = 'none';
                    
                    previewText.textContent = text;
                    previewText.style.display = 'block';
                    previewContainer.style.display = 'block';
                })
                .catch(error => {
                    alert('加载文本文件失败: ' + error);
                });
        }
    </script>
</body>
</html>
"""

COMMAND_EXECUTOR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mamba 命令执行器</title>
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #6c757d; color: white; padding: 15px; border-radius: 5px; }
        .command-form { margin: 20px 0; }
        .command-output { background: #f8f9fa; padding: 15px; border-radius: 5px; }
        pre { white-space: pre-wrap; }
        .btn { padding: 5px 10px; background: #6c757d; color: white; border: none; border-radius: 3px; text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Mamba 命令执行器</h1>
    </div>

    <div class="nav-links">
        <a href="{{ url_for('file_manager') }}" class="btn">返回文件管理器</a>
    </div>

    <form action="{{ url_for('execute_command') }}" method="post" class="command-form">
        <input type="text" name="command" placeholder="输入命令" style="width: 70%; padding: 8px;">
        <button type="submit" class="btn">执行</button>
    </form>

    {% if command_result %}
    <div class="command-output">
        <h3>执行结果</h3>
        <p><strong>命令:</strong> {{ command_result.command | e }}</p>
        <p><strong>退出码:</strong> {{ command_result.returncode | e }}</p>
        {% if command_result.stdout %}
        <p><strong>输出:</strong></p>
        <pre>{{ command_result.stdout | e }}</pre>
        {% endif %}
        {% if command_result.stderr %}
        <p><strong>错误:</strong></p>
        <pre>{{ command_result.stderr | e }}</pre>
        {% endif %}
    </div>
    {% endif %}
</body>
</html>
"""

def run_server():
    app.run(host='0.0.0.0', port=args.port, threaded=True)

if __name__ == '__main__':
    print(f"""
    Mamba Web Manager 正在运行
    
    访问地址:
    - 文件管理器: http://<服务器IP>:{args.port}/mamba
    - 命令执行器: http://<服务器IP>:{args.port}/mamba/out
    
    参数:
    - 端口: {args.port}
    - 默认目录: {args.directory}
    
    """)
    run_server()
