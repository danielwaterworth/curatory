#!env/bin/python
from curatory.app import app
app.jinja_env.auto_reload = True
app.run(debug=True)
