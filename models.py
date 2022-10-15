import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False, unique=True)
    channels = db.relationship("Channel", backref="user", lazy=True)
    chats = db.relationship("Chat", backref="user", lazy=True)

class Channel(db.Model):
    __tablename__ = "channels"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    username = db.Column(db.String, db.ForeignKey("users.username"), nullable=False)
    chats = db.relationship("Chat", backref="channel", lazy=True)

class Chat(db.Model):
    __tablename__ = "chats"
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String, nullable=False)
    username = db.Column(db.String, db.ForeignKey("users.username"), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    channelname = db.Column(db.String, db.ForeignKey("channels.name"), nullable=False)