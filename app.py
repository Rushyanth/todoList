from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, make_response
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from functools import wraps, update_wrapper
from datetime import datetime

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'todoList'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init MySQL
mysql = MySQL(app)



@app.route('/')
def home():
	return render_template('home.html')

# Class for Register Form
class RegisterForm(Form):
	name = StringField('Name', [validators.DataRequired()])
	email = StringField('Email', [validators.DataRequired()])
	username = StringField('Username', [validators.DataRequired()])
	password = PasswordField('Password', [
			validators.DataRequired(),
			validators.EqualTo('confirm', message='Passwords donot Match')
		])
	confirm = PasswordField('Confirm', [validators.DataRequired()])

# RegisterForm
@app.route('/register', methods = ['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		# Get the values from the form
		name = form.name.data 
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		# Create a cursor
		cur = mysql.connection.cursor()

		# Insert the values into the database
		cur.execute("INSERT into users (name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
		
		#Commit to database
		mysql.connection.commit ()

		# Close connection
		cur.close()

		flash("You are now registered and can login", "success")

		return render_template('login.html')

	return render_template('register.html', form = form)

# LoginForm
@app.route('/login', methods = ['GET','POST'])
def login():
	if request.method == 'POST':
		# Get form fields
		username = request.form['username']
		password = request.form['password']
		print(username);
		# Create cursor
		cur = mysql.connection.cursor()

		result = cur.execute("SELECT password from users WHERE username = %s", [username])

		app.logger.info(result)

		if result > 0:
			row = cur.fetchone()
			real_password = row['password']

			# Compare Passwords
			if sha256_crypt.verify(password, real_password) :
				# Passwords Matched
				
				session['logged_in'] = True
				session['username'] = username
				return redirect(url_for('userhome'))
			else:
				flash("passwords didnot match", "danger")
				return render_template('login.html')
		else:
			flash("User not found", "danger")
			return render_template('login.html')

		# Close cursor	
		cur.close()
	return render_template('login.html')

# Decorator to check if user is logged in
def isLoggedIn(f):
	print('called')
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash("Please login" , "danger")
			return redirect(url_for('login'))
	return wrap	


# User Home Page
@app.route('/userhome')
@isLoggedIn
def userhome():

	# Get the tasks to homepage
	# Create a cursor
	cur = mysql.connection.cursor()

	# Retreive data
	result = cur.execute("SELECT * from tasklist where username = %s", [session['username']])

	tasks = cur.fetchall()
	print(tasks)
	
	if result > 0 :
		# return render_template('userhome.html', tasks = tasks)
		response = make_response(render_template('userhome.html', tasks = tasks))
		response.headers['Last-Modified'] = datetime.now()
		response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
		response.headers['Pragma'] = 'no-cache'
		response.headers['Expires'] = '-1'
		return response
	else:
		response = make_response(render_template('userhome.html'))
		response.headers['Last-Modified'] = datetime.now()
		response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
		response.headers['Pragma'] = 'no-cache'
		response.headers['Expires'] = '-1'
		return response
	# Close cursor
	cur.close()

# Add Task
@app.route('/addTask', methods = ['GET', 'POST'])
@isLoggedIn
def addTask():
	if request.method == 'POST':
		# Get Task Details
		title = request.form['title']
		body = request.form['body']
		status = 'Not Done'

		# Create a cursor
		cur = mysql.connection.cursor()

		# Insert tasks into database
		cur.execute("INSERT into tasklist(title, body, status, username) VALUES(%s, %s, %s, %s)",
		(title, body, status, session['username']))

		# Commit the datbase
		mysql.connection.commit()

		# Close connection
		cur.close()
		flash("Task added successfully", "success")
		return redirect(url_for('userhome'))

	return render_template('addTask.html')

# Edit task
@app.route('/editTask/<string:id>', methods = ['GET', 'POST'])
@isLoggedIn
def editTask(id):
	# Create cursor
	cur = mysql.connection.cursor()

	# Get data
	result = cur.execute("SELECT * from tasklist where id = %s", [id])

	data = cur.fetchone()
	print(data)
	if request.method == 'POST':
		# Get Task Details
		title = request.form['title']
		body = request.form['body']
		status = 'Not Done'

		# Create a cursor
		cur = mysql.connection.cursor()

		# Insert tasks into database
		cur.execute("UPDATE tasklist set title=%s, body=%s where id=%s", (title, body, id))

		# Commit the datbase
		mysql.connection.commit()

		# Close connection
		cur.close()
		flash("Task Updated successfully", "success")

		return redirect(url_for('userhome'))

	return render_template('editTask.html', data= data)

# Delete Task
@app.route('/deleteTask/<string:id>', methods = ['GET', 'POST'])
@isLoggedIn
def deleteTask(id):
	# Create Cursor
	cur = mysql.connection.cursor()

	# Delete Data
	cur.execute("DELETE from tasklist where id = %s", [id])

	# Updating the auto increment id
	maxid = cur.execute("SELECT MAX(id) FROM tasklist ")
	print(maxid)
	print(type(maxid))
	cur.execute("ALTER TABLE tasklist AUTO_INCREMENT = %s", [maxid])

	# Commit the database
	mysql.connection.commit()

	# Close connection
	cur.close()

	flash("Deleted succesfully ", "danger")
	return redirect(url_for('userhome'))

# Status Of Task
@app.route('/statusOfTask/<string:status>/<string:id>', methods = ['POST', 'GET'])
@isLoggedIn
def statusOfTask(status,id):
	# Create Cursor
	cur = mysql.connection.cursor()

	# Change status
	if status == 'Not Done':
		status = 'Done'
	else:
		status = 'Not Done'
	cur.execute("UPDATE tasklist set status = %s where id = %s", (status, id))

	# Commit the database
	mysql.connection.commit()

	# Close connection
	cur.close()

	flash("Status changed succesfully ", "success")
	return redirect(url_for('userhome'))	

# Logout
@app.route('/logout')
@isLoggedIn
def logout():
	session.clear();
	flash("You are logged out")
	return redirect(url_for('login'))



if __name__ == '__main__':
	app.secret_key = "secret123"
	app.run(debug = True)














