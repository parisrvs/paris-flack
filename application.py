import os

from flask import Flask, session, render_template, url_for, redirect, request, jsonify
from flask_socketio import SocketIO, emit
from models import *
from flask_session import Session
from helpers import validate_email, validate_password, validate_username, sendmail
from werkzeug.security import check_password_hash, generate_password_hash
import random
import requests
from datetime import datetime

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)


@app.route("/", methods=["POST", "GET"])
def index():
    if session.get("username") == None:
        return redirect("/login")
    allchannels = Channel.query.order_by(Channel.name).all()
    
    if session.get("channelname") == None:
        session["channelname"] = None
        chats_current_channel = None
    else:
        ch = Channel.query.filter_by(name=session["channelname"]).first()
        if ch == None:
            session["channelname"] = None
            chats_current_channel = None            
        else:
            chats_current_channel = Chat.query.filter_by(channelname=session["channelname"]).order_by(Chat.time.desc()).limit(100).all()
    
    if request.method == "GET":        
        return render_template("homepage.html", username=session["username"], channelname=session["channelname"], allchannels=allchannels, chats_current_channel=chats_current_channel)


@app.route("/createchannel", methods=["POST", "GET"])
def createchannel():
    if session.get("username") == None:
        return redirect("/login")
    if request.method == "GET":
        return render_template("createchannel.html", username=session["username"])
    
    channelname = request.form.get("channelname")
    channelname = channelname.strip()
    if not channelname:
        return render_template("createchannel.html", username=session["username"], create_channel_error="Type a Channel Name")
    channelname = channelname.strip()
    c = Channel.query.filter_by(name=channelname).first()
    if c == None:
        c = Channel(name=channelname, username=session["username"])
        db.session.add(c)
        db.session.commit()
        session["channelname"] = channelname
        c = Channel.query.filter_by(name=channelname).first()
        socketio.emit("channel created", {"channel": channelname, "username": session["username"], "id": c.id}, broadcast=True)
        return redirect("/")
    else:
        return render_template("createchannel.html", username=session["username"], create_channel_error="Type a Different Channel Name")


@app.route("/deletechannel/<string:channelname>")
def deletechannel(channelname):
    if session.get("username") == None:
        return redirect("/login")
    c = Channel.query.filter_by(name=channelname).first()
    if c == None or c.username != session["username"]:
        return redirect("/")
    chats = c.chats
    for chat in chats:
        db.session.delete(chat)
        socketio.emit("deleted chat", {"success": True, "chat_id": str(chat.id), "channelname": chat.channelname}, broadcast=True)
    
    db.session.delete(c)    
    db.session.commit()
    socketio.emit("deleted channel", {"channelname": c.name, "channelid": c.id}, broadcast=True)
    if session["channelname"] == channelname:
        session["channelname"] = None
    return redirect("/")


@app.route("/editchat/<int:chat_id>", methods=["POST", "GET"])
def editchat(chat_id):
    if session.get("username") == None:
        return redirect("/login")

    try:
        chat_id = int(chat_id)
    except:
        return redirect("/")

    c = Chat.query.get(chat_id)
    if c == None:
        return redirect("/")
    else:
        channel = c.channelname

    if c.username != session["username"]:        
        return redirect("/")
    
    if request.method == "GET":
        return render_template("editchat.html", username=session["username"], chat=c)
    
    chat_message = request.form.get("chat_message")
    if not chat_message:
        return render_template("editchat.html", username=session["username"], chat=c, editchat_error="Type a Message")
    c.message = chat_message
    time = datetime.now()
    c.time = time
    db.session.commit()
    socketio.emit("deleted chat", {"success": True, "chat_id": chat_id, "channelname": c.channelname}, broadcast=True)
    mychat = {"message": chat_message, "channel": channel, "username": session["username"], "time": str(time), "chat_id": chat_id}
    socketio.emit("receive chat", mychat, broadcast=True)
    return redirect("/")



@app.route("/deletechat/<int:chat_id>")
def deletechat(chat_id):
    if session.get("username") == None:
        return redirect("/login")

    try:
        chat_id = int(chat_id)
    except:
        return redirect("/")

    c = Chat.query.get(chat_id)
    if c == None:
        return redirect("/")

    if c.username != session["username"]:        
        return redirect("/")
    db.session.delete(c)
    db.session.commit()    
    socketio.emit("deleted chat", {"success": True, "chat_id": chat_id, "channelname": c.channelname}, broadcast=True)
    return redirect("/")


@app.route("/changechannel/<string:channelname>")
def changechannel(channelname):
    if session.get("username") == None:
        return redirect("/login")
    session["channelname"] = channelname
    return redirect("/")




@app.route("/login", methods=["POST", "GET"])
def login():
    if session.get("username") != None:
        return redirect("/")
    
    session.clear()    
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return render_template("login.html", login_error="enter username/email and password")
    
    username = username.strip()
    user = User.query.filter_by(username=username).first()
    if user == None:
        user = User.query.filter_by(email=username).first()
        if user == None:
            return render_template("login.html", login_error="Incorrect Username or Email")
    
    if check_password_hash(user.password, password):
        session["username"] = user.username
        session.permanent = True
        return redirect("/")
    else:
        return render_template("login.html", login_error="Incorrect Password")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/register", methods=["POST", "GET"])
def register():
    if session.get("username") != None:
        return redirect("/")
    session.clear()

    if request.method == "GET":
        return render_template("register.html")
    
    username = request.form.get("username")
    password = request.form.get("password")
    password1 = request.form.get("password1")
    email = request.form.get("email")

    if not username or not password or not email or not password1:
        return render_template("register.html", register_error="Input in all fields marked with *.")

    if not validate_email(email):
        return render_template("register.html", register_error="Invalid Email Address")

    if not validate_password(password):
        return render_template("register.html", register_error="Alpha-numeric Password Required")
    
    if password != password1:
        return render_template("register.html", register_error="Passwords Don't Match")
    
    if not validate_username(username):
        return render_template("register.html", register_error="Invalid Username")

    username = username.strip()
    password = password.strip()
    email = email.strip()

    user = User.query.filter_by(username=username).first()
    if user != None:
        return render_template("register.html", register_error="This Username already exists.")
    user = User.query.filter_by(email=email).first()
    if user != None:
        return render_template("register.html", register_error="This Email is associated with another account.")

    password = generate_password_hash(password)
    code = str(random.randint(100000, 999999))
    session["user_registration"] = {"username": username, "password": password, "email": email, "code": code}
    try:
        sendmail(email, "Verify Email", code)
    except:
        return redirect("/process_verification")
    return redirect("/verification")


@app.route("/verification", methods=["POST", "GET"])
def verification():
    if session.get("user_registration") == None:
        return redirect("/")
    
    if request.method == "GET":
        return render_template("verification.html", email=session["user_registration"]["email"])
    
    code = request.form.get("code")
    if not code:
        return render_template("verification.html", email=session["user_registration"]["email"], verification_error="enter verification code")
    if code != session["user_registration"]["code"]:
        return render_template("verification.html", email=session["user_registration"]["email"], verification_error="incorrect verification code")
    return redirect("/process_verification")


@app.route("/resend_verification_code")
def resend_verification_code():
    if session.get("user_registration") == None:
        return redirect("/")
    
    code = str(random.randint(100000, 999999))
    session["user_registration"]["code"] = code
    try:
        sendmail(session["user_registration"]["email"], "Verify Email", code)
    except:
        return redirect("/process_verification")
    return redirect("/verification")

@app.route("/process_verification")
def process_verification():
    if session.get("user_registration") == None:
        return redirect("/")

    user = User(email=session["user_registration"]["email"], password=session["user_registration"]["password"], username=session["user_registration"]["username"])
    db.session.add(user)
    db.session.commit()
    try:
        sendmail(session["user_registration"]["email"], "Registration Successful", "Thankyou for registering with paris-flack.")
    except:
        pass
    session.clear()
    return redirect("/login")

@app.route("/forgotpassword", methods=["POST", "GET"])
def forgotpassword():
    if session.get("username") != None:
        return redirect("/")
    
    session.clear()
    if request.method == "GET":
        return render_template("forgotpassword.html")
    
    username = request.form.get("username")
    if not username:
        return render_template("forgotpassword.html", fp_error="enter username or email address")
    
    username = username.strip()
    user = User.query.filter_by(username=username).first()
    if user == None:
        user = User.query.filter_by(email=username).first()
        if user == None:
            return render_template("login.html", login_error="Incorrect Username or Email")
    
    code = str(random.randint(100000, 999999))
    session["fp_userInfo"] = {"user": user, "code": code}
    try:
        sendmail(user.email, "Verify Email", code)
    except:
        return "Error"
    return redirect("/fp_verification")

@app.route("/fp_verification", methods=["POST", "GET"])
def fp_verification():
    if session.get("fp_userInfo") == None:
        return redirect("/")

    if request.method == "GET":
        return render_template("fp_verification.html", email=session["fp_userInfo"]["user"].email)

    code = request.form.get("code")
    if not code:
        return render_template("fp_verification.html", email=session["fp_userInfo"]["user"].email, fp_verification_error="Type Verification Code")
    if code != session["fp_userInfo"]["code"]:
        return render_template("fp_verification.html", email=session["fp_userInfo"]["user"].email, fp_verification_error="Incorrect Verification Code")
    
    username = session["fp_userInfo"]["user"].username
    session.clear()
    session["username"] = username
    return redirect("/changepassword")


@app.route("/changepassword", methods=["POST", "GET"])
def changepassword():
    if session.get("username") == None:
        return redirect("/login")
    if request.method == "GET":
        return render_template("changepassword.html", username=session["username"])

    password = request.form.get("password")
    password1 = request.form.get("password1")

    if not password or not password1:
        return render_template("changepassword.html", username=session["username"], change_password_error="password or confirm password missing")
    if password != password1:
        return render_template("changepassword.html", username=session["username"], change_password_error="passwords don't match")
    if not validate_password(password):
        return render_template("changepassword.html", username=session["username"], change_password_error="min 6 character alpha-numeric password")

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        session.clear()
        return redirect("/login")

    password = generate_password_hash(password)
    user.password = password
    db.session.commit()
    sendmail(user.email, "Security Information", "Password Changed for 'paris-flack'")
    return redirect("/")


@app.route("/fp_resend_verification_code")
def fp_resend_verification_code():
    if session.get("fp_userInfo") == None:
        return redirect("/")

    code = str(random.randint(100000, 999999))
    session["fp_userInfo"]["code"] = code
    try:
        sendmail(session["fp_userInfo"]["user"].email, "Verify Email", code)
    except:
        return "Error"
    return redirect("/fp_verification")


@app.route("/if_channel")
def if_channel():
    res = {}
    if session.get("channelname") == None:
        res["channel"] = False
    else:
        res["channel"] = session["channelname"]

    if session.get("username") == None:
        res["username"] = False
    else:
        res["username"] = session["username"]

    return jsonify(res)


@socketio.on("submit chat")
def chat(data):
    message = data["message"]
    channel = data["channel"]
    username = data["username"]
    time = datetime.now()
    c = Chat(message=message, username=username, time=time, channelname=channel)
    db.session.add(c)
    db.session.commit()
    c = Chat.query.filter_by(username=username).filter_by(channelname=channel).filter_by(time=time).first()
    mychat = {"message": message, "channel": channel, "username": username, "time": str(time), "chat_id": c.id}
    emit("receive chat", mychat, broadcast=True)



@socketio.on("process channel deletion")
def channel_deletion(data):
    emit("block chat", {"channelname": data["channelname"]}, broadcast=True)
    

@socketio.on("delete chat")
def delchat(data):
    chat_id = data["chat_id"]

    try:
        chat_id = int(chat_id)
    except:
        emit("deleted chat", {"success": False}, broadcast=False)

    c = Chat.query.get(chat_id)
    if c == None:
        emit("deleted chat", {"success": False}, broadcast=False)
    
    if c.username != session["username"]:
        emit("deleted chat", {"success": False}, broadcast=False)
    
    chat_id = str(c.id)
    db.session.delete(c)
    db.session.commit()
    emit("deleted chat", {"success": True, "chat_id": chat_id, "channelname": c.channelname}, broadcast=True)
