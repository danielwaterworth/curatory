from flask import Flask
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oeshuadaligd.ih/,'
Bootstrap(app)
from curatory.app import views
