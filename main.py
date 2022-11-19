import os,re,io
import MySQLdb.cursors
from PIL import Image
from flask import Flask, redirect, render_template, request, session, url_for
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from ibm_watson_machine_learning import APIClient
import tarfile,base64
from keras.models import load_model
from keras.preprocessing import image
import numpy as np
import smtplib

WMLCredentials = {
    "url": "https://eu-de.ml.cloud.ibm.com",
    "apikey": "otPqZJ572G9Kvgqd5eTuHSeZ-ktrTokqdXvWd8kaFXLv"
}
client = APIClient(WMLCredentials)
client.set.default_space("12f0d23b-8918-45db-a632-01c21bee5035")
model_id = "9a345915-1cbd-41de-938a-7c04ede93f31"

try:
    client.repository.download(model_id, 'dn.tgz')
    model = tarfile.open('dn.tgz')
    model.extractall('.')
    model.close()
except:
    print("File exists!!")

app = Flask(__name__)
app.secret_key = 'abc123'
UPLOAD_FOLDER = os.path.join('static', 'uploads')

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Jan2021!'
app.config['MYSQL_DB'] = 'ibmproj'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)

# configuration of mail
app.config['MAIL_SERVER']='smtp-relay.sendinblue.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'digital.naturalist@yahoo.com'
app.config['MAIL_PASSWORD'] = 'zYjFPqIAK78UMg5d'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
   
@app.route('/', methods=['GET', 'POST'])
def login():
    msg = '' # Output message
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/uploaded', methods=['GET','POST'])
def uploaded():
    if 'loggedin' in session:
        if request.method=='POST':
            imagereceived = request.files['imageUpload']
            img_filename = secure_filename(imagereceived.filename)
            imagereceived.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
            print(imagereceived)
            return redirect(url_for('showimage', filename=img_filename))
        return render_template('home.html', uploaded_image=os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
    return redirect(url_for('login'))

@app.route('/showimage')
def showimage():
    if 'loggedin' in session:
        img_filename = request.args['filename']
        model = load_model('final_model.h5')
        classes = ['Corpse Flower','Great Indian Bustard Bird','Lady Slipper Orchid Flower',
                   'Pangolin Mammal','Senenca White Deer Mammal','Spoon Billed Sandpiper Bird']
        
        img = image.load_img(os.path.join(app.config['UPLOAD_FOLDER'], img_filename), target_size=(64, 64))
        img = image.img_to_array(img)
        img = np.expand_dims(img, axis=0)
        pred = np.argmax(model.predict(img), axis=1)
        print(pred)
        print('Prediction: ', classes[pred[0]])
        cursor = mysql.connection.cursor()
        fil = open(os.path.join(app.config['UPLOAD_FOLDER'], img_filename), 'rb').read()
        # We must encode the file to get base64 string
        fil = base64.b64encode(fil)
        cursor.execute('INSERT INTO imagetable (photo,username,pred) VALUES (%s,%s,%s)',
                       (fil, session['username'], classes[pred[0]]))
        mysql.connection.commit()
        return render_template(
            'showimage.html', uploaded_image=os.path.join(app.config['UPLOAD_FOLDER'], img_filename), prediction=classes[pred[0]])
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM accounts WHERE username = %s OR email = %s', (username,email))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute(
                'INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            
            msg1 = Message(
                'Confirmation Mail - Digital Naturalist',
                sender ='digital.naturalist@yahoo.com',
                recipients = [email]
               )
            msg1.body = 'This mail is to inform you that your account has been sucessfully registered\n\nUsername: ' + username + '\nPassword: ' + password + '\n'
            mail.send(msg1)
            

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

@app.route('/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s',
                       (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/history')
def history():
    cursor = mysql.connection.cursor()
    cursor.execute(
        'SELECT photo,pred FROM IMAGETABLE WHERE username = %s ORDER BY date_entry DESC', (session['username'],))
    data = cursor.fetchall()
    if len(data) == 0:
        return render_template('errorpage.html', message="No History found!!")
    images = []
    preds = []
    for item in data:
        (image,pred) = item
        binary_data = base64.b64decode(image)
        im = io.BytesIO(binary_data)
        encoded_img_data = base64.b64encode(im.getvalue())
        images.append(encoded_img_data.decode('utf-8'))
        preds.append(pred)
    return render_template('history.html', photos = images, preds = preds)