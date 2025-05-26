
from . import app
from flask import render_template, jsonify

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ping')
def ping():
    return jsonify({'mensaje': '¡Hola desde Flask + uWSGI + Nginx!'})
