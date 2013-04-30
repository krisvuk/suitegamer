import os
import re
import random
import hashlib
import urllib2
import hmac
from google.appengine.api import urlfetch
from google.appengine.api import users
from string import letters
from google.appengine.api import images
from google.appengine.ext import blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import PIL
import datetime
import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)



secret = 'ID,fmkf458FDHhfJIJ9j%^%hY77RRF76gb.2'


username = ''


def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class MainHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))


def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

class MainPage(MainHandler):
    def get(self):
	if self.user:
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
            for clan in team_name:
                team_name = clan.team_name_anycase
            self.render('index.html', team_name = team_name, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)
        else:
            self.render('index.html')

    def post(self):
	username = self.request.get('username').lower()
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/dashboard/%s' %username)
        else:
            msg = 'Invalid login.'
            self.render('login.html', error = msg)	


##### user stuff
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)     
    
class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    first_name = db.StringProperty(required = True)
    last_name = db.StringProperty(required = True)
    country = db.StringProperty(required = True)
    month = db.StringProperty(required = True)
    day = db.StringProperty(required = True)
    year = db.StringProperty(required = True)
  
  
    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u
    
    @classmethod
    def by_email(cls, email):
        e = User.all().filter('email =', email).get()
        return e

    @classmethod
    def register(cls, name, pw, email = None, first_name = None, last_name = None, country = None, month = None, day = None, year = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email,
		    first_name = first_name,
                    last_name = last_name,
                    country = country,
                    month = month,
                    day = day,
                    year = year)
	

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u

class Teams(db.Model):
    name = db.StringProperty(required = True)
    team_name = db.StringProperty()
    team_name_anycase = db.StringProperty()
    founder = db.StringProperty()
    last_modified = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_team(cls, team_name):
        u = Teams.all().filter('team_name =', team_name).get()
        return u


class Streams(db.Model):
    username = db.StringProperty(required = True)
    stream_url = db.StringProperty()
    stream_name = db.StringProperty()
    stream_title = db.StringProperty()
    tracking_value = db.StringProperty()
    embedded_stream = db.TextProperty()

    @classmethod
    def stream_type(self, b):
        url = str(b)
        if url.find('twitch') == -1:
            return 'Own3D.tv'
        else:
            return 'Twitch.tv' 

    @classmethod
    def by_name(cls, stream_name):
        e = Streams.all().filter('stream_name =', stream_name).get()
        return e

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_title(cls, stream_title):
        e = Streams.all().filter('stream_title =', stream_title).get()
        return e

    
class Tracking_Streams(db.Model):
    username = db.StringProperty(required = True)
    stream_url = db.StringProperty()
    stream_name = db.StringProperty()
    stream_title = db.StringProperty()
    tracking_value = db.StringProperty()
    embedded_stream = db.TextProperty()
    streamid = db.TextProperty()

    @classmethod
    def stream_type(self, b):
        url = b
        if url.find('twitch') == -1:
            return 'Own3D.tv'
        else:
            return 'Twitch.tv'
    @classmethod
    def check_if_live_twitch(self, b):
        url = ('http://api.justin.tv/api/stream/summary.xml?channel=%s' %b)
        result = urlfetch.fetch(url)
        check = result.content
        if (check).find('<streams_count>1</streams_count>') == -1:
            return 'Offline'
        else:
            return 'Live'

    @classmethod
    def check_if_live_own3d(self, b):
        url = (b)
        result = urlfetch.fetch(url)
        check = result.content
        a = check.find('http://www.own3d.tv/liveembed/')
        b = check.find('"></iframe>')
        stream_id = check[a + 30:b]
        url2 = ('http://api.own3d.tv/rest/live/list')
        result2 = urlfetch.fetch(url2)
        check2 = result2.content
        if (check2).find(stream_id) == -1:
            return 'Offline'
        else:
            return 'Live'

    @classmethod
    def by_name(cls, stream_name):
        e = Tracking_Streams.all().filter('stream_name =', stream_name).get()
        return e

    @classmethod
    def by_title(cls, stream_title):
        e = Tracking_Streams.all().filter('stream_title =', stream_title).get()
        return e

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

class Rating(db.Model):
    name_of_profile = db.StringProperty(required = True)
    name_of_submitted = db.StringProperty(required = True)
    post = db.TextProperty()
    rating = db.FloatProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now_add = True)
    
class Profile_Posts(db.Model):
    name_of_profile = db.StringProperty(required = True)
    name_of_submitted = db.StringProperty(required = True)
    name_of_submitted_team = db.StringProperty()
    post = db.TextProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now_add = True)

    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    def render(self):
        self._render_text = self.post.replace('\n', '<br>')
        return render_str("profile.html", post = self)

class Profile_Broadcast(db.Model):
    name_of_profile = db.StringProperty(required = True)
    name_of_submitted = db.StringProperty(required = True)
    broadcast = db.TextProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now_add = True)

    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    def render(self):
        self._render_text = self.post.replace('\n', '<br>')
        return render_str("profile.html", post = self)


class Profile_Images(db.Model):
    name = db.StringProperty(required = True)
    image = db.BlobProperty()
    last_modified = db.DateTimeProperty(auto_now_add = True)

class Profile_Games(db.Model):
    name = db.StringProperty(required = True)
    game1 = db.StringProperty()
    game2 = db.StringProperty()
    game3 = db.StringProperty()


class Handles(db.Model):
    name = db.StringProperty(required = True)
    handle = db.StringProperty()
    
##Regular Expressions

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASSWORD_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASSWORD_RE.match(password)

EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return email and EMAIL_RE.match(email)




class SignUp(MainHandler):
    def get(self):
        self.render("register.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify_password = self.request.get('verify_password')
        self.email = self.request.get('email')
	self.firstname = self.request.get('firstname')
	self.lastname = self.request.get('lastname')
	self.country = self.request.get('country')
	self.month = self.request.get('month')
	self.day = self.request.get('day')
	self.year = self.request.get('year')

        params = dict(username = self.username, email = self.email, first_name=self.first_name, verify_password = self.verify_password, lastname = self.lastname, country = self.country, month = self.month, day = self.day, year = self.year)

        if not valid_username(self.username):
            params['username_error'] = "Invalid username (or blank)."
            have_error = True

        if not valid_password(self.password):
            params['password_error'] = "That wasn't a valid password."
            have_error = True
            
        elif self.password != self.verify_password:
            params['password_verify_error'] = "Your passwords didn't match."
            have_error = True

        if not self.country:
            params['country_error'] = "Country required."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

	if not self.firstname:
	    params['error_firstname'] = "Firstname is required."
            have_error = True
            
	if not self.lastname:
	    params['error_lastname'] = "Lastname is required."
            have_error = True
            
	if not self.month:
	    params['error_birthday'] = "A full birth day is required."
            have_error = True

	if not self.day:
	    params['error_birthday'] = "A full birth day is required."
            have_error = True

	if not self.year:
	    params['error_birthday'] = "A full birth day is required."
            have_error = True
            
        if have_error:
            self.render('register.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError
            

class Register(SignUp):

    def get(self):
        if self.user:
            self.redirect('/')
        else:
            self.render('register.html')
    
    def done(self):
        #make sure the user doesn't already exist
	e = User.by_email(self.email.lower())
        u = User.by_name(self.username.lower())
        if u and e:
            msg = 'That user already exists.'
            msg1 = 'That email is already in use.'
            self.render('register.html', error_username = msg, error_email = msg1)
	elif u:
            msg = 'That user already exists.'
            self.render('register.html', error_username = msg)
	elif e:
            msg1 = 'That email is already in use.'
            self.render('register.html', error_email = msg1)
        else:
            u = User.register(self.username.lower(), self.password, self.email.lower(), self.firstname, self.lastname, self.country, self.month, self.day, self.year)
            u.put()

            self.login(u)
            self.redirect('/dashboard/%s' %self.username)
	
        

class Login(MainHandler):
    def get(self):
        self.render('login.html')

    def post(self):
        username = self.request.get('username').lower()
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/dashboard/%s' %username)
        else:
            msg = 'Invalid login. Please try again.'
            self.render('login.html', error = msg)

class Logout(MainHandler):
    def get(self):
        self.logout()
        self.redirect('/')

class Dashboard(MainHandler):
    def get(self, profile_id):
        u = User.by_name(profile_id.lower())
        if not u:
            self.redirect('/error')
        elif self.user.name == profile_id:
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", profile_id)
            for clan in team_name:
                team_name = clan.team_name_anycase
            self.render('dashboard.html', team_name = team_name, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)


class Stream_One(MainHandler):
    def get(self, stream_one):
        if self.user:
            stream_bed1 = ''
            current_user = str(self.user.name)
            streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", current_user)
            for clan in team_name:
                team_name = clan.team_name_anycase
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream
            self.render('stream_one.html', team_name = team_name, stream_bed1 = stream_bed1, tracking_streams = tracking_streams, streams = streams, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')

    def post(self, stream_one):
        stream_two_name = self.request.get("stream_from_two")
        self.redirect('/stream_two/%s/%s' %(stream_one, stream_two_name))
        

class Stream_Two(MainHandler):
    def get(self, stream_one, stream_two):
        if self.user:
            stream_bed1 = ''
            stream_bed2 = ''
            current_user = str(self.user.name)
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
            streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", current_user)
            for clan in team_name:
                team_name = clan.team_name_anycase
            
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            
            streams3 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_two)
            tracking_streams3 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_two)
            
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream

            e2 = Streams.by_title(stream_two)
            f2 = Tracking_Streams.by_title(stream_two)
            if e2:
                for stream_ in streams3:
                    stream_bed2 = stream_.embedded_stream
            elif f2:
                for tracking_ in tracking_streams3:
                    stream_bed2 = tracking_.embedded_stream
            self.render('stream_two.html', team_name = team_name, stream_bed1 = stream_bed1, stream_bed2 = stream_bed2, tracking_streams = tracking_streams, streams = streams, stream_two = stream_two, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')

    def post(self, stream_one, stream_two):
        stream_three_name = self.request.get("stream_from_three")
        self.redirect('/stream_three/%s/%s/%s' %(stream_one, stream_two, stream_three_name))

class Stream_Three(MainHandler):
    def get(self, stream_one, stream_two, stream_three):
        if self.user:
            stream_bed1 = ''
            stream_bed2 = ''
            stream_bed3 = ''
            current_user = str(self.user.name)
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
            streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", current_user)
            for clan in team_name:
                team_name = clan.team_name_anycase
            
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            
            streams3 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_two)
            tracking_streams3 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_two)

            streams4 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_three)
            tracking_streams4 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_three)
            
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream

            e2 = Streams.by_title(stream_two)
            f2 = Tracking_Streams.by_title(stream_two)
            if e2:
                for stream_ in streams3:
                    stream_bed2 = stream_.embedded_stream
            elif f2:
                for tracking_ in tracking_streams3:
                    stream_bed2 = tracking_.embedded_stream

            e3 = Streams.by_title(stream_three)
            f3 = Tracking_Streams.by_title(stream_three)
            if e3:
                for stream_ in streams4:
                    stream_bed3 = stream_.embedded_stream
            elif f3:
                for tracking_ in tracking_streams4:
                    stream_bed3 = tracking_.embedded_stream
            self.render('stream_three.html', team_name = team_name, stream_bed1 = stream_bed1, stream_bed2 = stream_bed2, stream_bed3 = stream_bed3, tracking_streams = tracking_streams, streams = streams, stream_three = stream_three, stream_two = stream_two, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')

    def post(self, stream_one, stream_two, stream_three):
        stream_four_name = self.request.get("stream_from_four")
        self.redirect('/stream_four/%s/%s/%s/%s' %(stream_one, stream_two, stream_three, stream_four_name))

class Stream_Four(MainHandler):
    def get(self, stream_one, stream_two, stream_three, stream_four):
        if self.user:
            stream_bed1 = ''
            stream_bed2 = ''
            stream_bed3 = ''
            stream_bed4 = ''
            current_user = str(self.user.name)
            streams2 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_one)
            tracking_streams2 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_one)
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", current_user)
            for clan in team_name:
                team_name = clan.team_name_anycase
            
            streams3 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_two)
            tracking_streams3 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_two)

            streams4 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_three)
            tracking_streams4 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_three)

            streams5 = db.GqlQuery("select * from Streams WHERE stream_title =:1", stream_four)
            tracking_streams5 = db.GqlQuery("select * from Tracking_Streams WHERE stream_title =:1", stream_four)
            
            e = Streams.by_title(stream_one)
            f = Tracking_Streams.by_title(stream_one)
            if e:
                for stream_ in streams2:
                    stream_bed1 = stream_.embedded_stream
            elif f:
                for tracking_ in tracking_streams2:
                    stream_bed1 = tracking_.embedded_stream

            e2 = Streams.by_title(stream_two)
            f2 = Tracking_Streams.by_title(stream_two)
            if e2:
                for stream_ in streams3:
                    stream_bed2 = stream_.embedded_stream
            elif f2:
                for tracking_ in tracking_streams3:
                    stream_bed2 = tracking_.embedded_stream

            e3 = Streams.by_title(stream_three)
            f3 = Tracking_Streams.by_title(stream_three)
            if e3:
                for stream_ in streams4:
                    stream_bed3 = stream_.embedded_stream
            elif f3:
                for tracking_ in tracking_streams4:
                    stream_bed3 = tracking_.embedded_stream

            e4 = Streams.by_title(stream_four)
            f4 = Tracking_Streams.by_title(stream_four)
            if e4:
                for stream_ in streams5:
                    stream_bed4 = stream_.embedded_stream
            elif f4:
                for tracking_ in tracking_streams5:
                    stream_bed4 = tracking_.embedded_stream
            self.render('stream_four.html',  team_name = team_name, stream_bed1 = stream_bed1, stream_bed2 = stream_bed2, stream_bed3 = stream_bed3, stream_bed4 = stream_bed4, stream_four = stream_four, stream_three = stream_three, stream_two = stream_two, stream_one = stream_one, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            redirect('/register')


class Add_Stream(MainHandler):
    def get(self):
        current_user = str(self.user.name)
        if self.user:
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", current_user)
            for clan in team_name:
                team_name = clan.team_name_anycase
            self.render('add_stream.html', team_name = team_name, username = self.user.name, firstname=self.user.first_name, lastname= self.user.last_name)
        else:
            redirect('/register')

    def post(self):
        tracking_streams = ''
        checkss2 = ''
        stream_url = self.request.get('stream_url')
        stream_title = self.request.get('stream_title')
        current_user = self.user.name
        check = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
        checkss = ''
        check_if_twitch = str(stream_url.find('http://www.twitch.tv/'))
        check_if_own3d = str(stream_url.find('http://www.own3d.tv/'))
        check_if_track = self.request.get('if_track')
        streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
        for checks in check:
            checkss = checks.stream_url
        for checks2 in check:
            checkss2 = checks2.stream_title
        if stream_url == '':
            error = "You must enter a valid url and a title."
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title, error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif checkss == stream_url:
            error = ("You are already tracking %s." %stream_url)
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title, error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif not check_if_track:
            error = ("You did not elect to track or not track this stream.")
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title, error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif not stream_title:
            error = ("You did not enter a valid stream title (3-12 characters).")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)

            
        elif checkss2 == stream_title:
            error = ("You have already used the name %s. " %stream_title)
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)

        elif stream_title.find(' ') != -1:
            error = ("Your title cannot have any spaces.")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
            
        elif len(stream_title) > 14:
            error = ("Your title cannot be over 14 characters.")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif check_if_track == "True" and int(streams_tracking_count) >= 12:
            error = ("You cannot track more than 12 streams.")
            self.render('add_stream.html',stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        elif check_if_twitch == "0":
            if check_if_track == "True":
                tracking_streams = Tracking_Streams(username = self.user.name)
                streamupl = self.request.get('stream_url')
                tracking_streams.stream_url = (streamupl)
                stream_nameupl = self.request.get('stream_url')
                tracking_streams.stream_name = (stream_nameupl[(stream_nameupl.find('.tv/')+ 4):])
                stream_track = self.request.get('if_track')
                tracking_streams.tracking_value = (stream_track)
                stream_titleupl = self.request.get('stream_title')
                tracking_streams.embedded_stream = ('<object type="application/x-shockwave-flash" height="365" width="598" id="live_embed_player_flash" data="http://www.twitch.tv/widgets/live_embed_player.swf?channel=%s" bgcolor="#000000"><param name="allowFullScreen" value="true" /><param name="allowScriptAccess" value="always" /><param name="allowNetworking" value="all" /><param name="movie" value="http://www.twitch.tv/widgets/live_embed_player.swf" /><param name="flashvars" value="hostname=www.twitch.tv&channel=%s&auto_play=true&start_volume=25" /></object>' %(tracking_streams.stream_name, tracking_streams.stream_name))
                tracking_streams.stream_title = (stream_titleupl)
                tracking_streams.put()
                self.redirect('/dashboard/%s' %self.user.name)
            else:
                streams = Streams(username = self.user.name)
                streamupl = self.request.get('stream_url')
                streams.stream_url = (streamupl)
                stream_nameupl = self.request.get('stream_url')
                streams.stream_name = (stream_nameupl[(stream_nameupl.find('.tv/')+ 4):])
                stream_track = self.request.get('if_track')
                streams.tracking_value = (stream_track)
                stream_titleupl = self.request.get('stream_title')
                streams.embedded_stream = ('<object type="application/x-shockwave-flash" height="365" width="598" id="live_embed_player_flash" data="http://www.twitch.tv/widgets/live_embed_player.swf?channel=%s" bgcolor="#000000"><param name="allowFullScreen" value="true" /><param name="allowScriptAccess" value="always" /><param name="allowNetworking" value="all" /><param name="movie" value="http://www.twitch.tv/widgets/live_embed_player.swf" /><param name="flashvars" value="hostname=www.twitch.tv&channel=%s&auto_play=true&start_volume=25" /></object>' %(streams.stream_name, streams.stream_name))
                streams.stream_title = (stream_titleupl)
                streams.put()
                self.redirect('/dashboard/%s' %self.user.name)
        elif check_if_own3d== "0":
            if check_if_track == "True":
                tracking_streams = Tracking_Streams(username = self.user.name)
                url = self.request.get('stream_url')
                result = urlfetch.fetch(url)
                check = result.content
                a = check.find('http://www.own3d.tv/liveembed/')
                b = check.find('"></iframe>')
                tracking_streams.streamid = check[a + 30:b]
                streamupl = self.request.get('stream_url')
                tracking_streams.stream_url = (streamupl)
                stream_nameupl = self.request.get('stream_url')
                tracking_streams.stream_name = (stream_nameupl[(stream_nameupl.find('.tv/')+ 4):])
                stream_track = self.request.get('if_track')
                tracking_streams.tracking_value = (stream_track)
                stream_titleupl = self.request.get('stream_title')
                tracking_streams.embedded_stream = ('<iframe height="365" width="598" frameborder="0" src="http://www.own3d.tv/liveembed/%s"></iframe>' %tracking_streams.streamid)
                tracking_streams.stream_title = (stream_titleupl)
                tracking_streams.put()
                self.redirect('/dashboard/%s' %self.user.name)
            else:
                streams = Streams(username = self.user.name)
                url = self.request.get('stream_url')
                result = urlfetch.fetch(url)
                check = result.content
                a = check.find('http://www.own3d.tv/liveembed/')
                b = check.find('"></iframe>')
                streams.stream_id = check[a + 30:b]
                streamupl = self.request.get('stream_url')
                streams.stream_url = (streamupl)
                stream_nameupl = self.request.get('stream_url')
                streams.stream_name = (stream_nameupl[(stream_nameupl.find('.tv/')+ 4):])
                stream_track = self.request.get('if_track')
                streams.tracking_value = (stream_track)
                stream_titleupl = self.request.get('stream_title')
                streams.embedded_stream = ('<iframe height="365" width="598" frameborder="0" src="http://www.own3d.tv/liveembed/%s"></iframe>' %streams.streamid)
                streams.stream_title = (stream_titleupl)
                streams.put()
                self.redirect('/dashboard/%s' %self.user.name)
        else:
            error = "You must enter a valid url (own3d.tv or twitch.tv)."
            self.render('add_stream.html', stream_url = stream_url, stream_title = stream_title,  error = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)

class Stream_Tracking_List(MainHandler):
    def get(self):
        tracking_streams = ''
        current_user = self.user.name
        tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1 ", current_user)
        streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
        self.render('stream_tracking_list.html', x = 0, tracking_streams = tracking_streams, streams = streams, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)


class My_Streams(MainHandler):
    def get(self, profile_id):
        current_user = self.user.name
        streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
        streams_count2 = (db.GqlQuery("select * from Streams WHERE username =:1", current_user)).count()
        self.render('my_streams.html',streams_count = (streams_tracking_count+streams_count2), streams_tracking_count = streams_tracking_count,  username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)

    def post(self):
        current_user = self.user.name
        url = self.request.get('url')
        tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE stream_url =:1", url)
        for stream_url_ in tracking_streams:
            stream_url = stream_url_.stream_url
        for stream_name_ in tracking_streams:
            stream_name = stream_name_.stream_name
        for stream_title_ in tracking_streams:
            stream_title = stream_title_.stream_title
        for stream_embedded_stream_ in tracking_streams:
            stream_embedded_stream = stream_embedded_stream_.embedded_stream
        streams = Streams(username = self.user.name, stream_url = stream_url, stream_name = stream_name, stream_title = stream_title, tracking_value = 'False', embedded_stream = stream_embedded_stream)
        streams.put()
        the_stream = self.request.get('untrack')
        q = Tracking_Streams.get_by_id(int(the_stream), parent=None)
        db.delete(q)
        self.redirect('/my_streams/%s' %current_user)


class My_Streams_List(MainHandler):
    def get(self):
        tracking_streams = ''
        current_user = self.user.name
        streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
        tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
        streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
        streams_count2 = (db.GqlQuery("select * from Streams WHERE username =:1", current_user)).count()
        self.render('my_streams_list.html', streams_count = (streams_tracking_count+streams_count2), streams_tracking_count = streams_tracking_count, tracking_streams = tracking_streams, streams = streams, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)

    def post(self):
        current_user = self.user.name
        streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
        if self.request.get('untrack'):
            stream_url1 = ''
            stream_name1 = ''
            stream_title1 = ''
            stream_tracking_value1 = ''
            stream_embedded_stream1 = ''
            current_user = self.user.name
            stream_id = self.request.get('url')
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE stream_url =:1", stream_id)
            for stream_url_ in tracking_streams:
                stream_url1 = stream_url_.stream_url
            for stream_name_ in tracking_streams:
                stream_name1 = stream_name_.stream_name
            for stream_title_ in tracking_streams:
                stream_title1 = stream_title_.stream_title
            for stream_tracking_value_ in tracking_streams:
                stream_tracking_value1 = stream_tracking_value_.tracking_value
            for stream_embedded_stream_ in tracking_streams:
                stream_embedded_stream1 = stream_embedded_stream_.embedded_stream
            streams = Streams(username = self.user.name, stream_url = stream_url1, stream_name = stream_name1, stream_title = stream_title1, tracking_value = 'False', embedded_stream = stream_embedded_stream1)
            streams.put()
            the_stream = self.request.get('untrack')
            q = Tracking_Streams.get_by_id(int(the_stream), parent=None)
            db.delete(q)
            self.redirect('/my_streams/%s' %current_user)
        elif self.request.get('track'):
            if int(streams_tracking_count) >= 12:
                tracking_streams = ''
                current_user = self.user.name
                streams = db.GqlQuery("select * from Streams WHERE username =:1", current_user)
                tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)
                streams_tracking_count = (db.GqlQuery("select * from Tracking_Streams WHERE username =:1", current_user)).count()
                streams_count2 = (db.GqlQuery("select * from Streams WHERE username =:1", current_user)).count()
                self.redirect('/my_streams/%s' %current_user)
            else:    
                stream_url2 = ''
                stream_name2 = ''
                stream_title2 = ''
                stream_tracking_value2 = ''
                stream_embedded_stream2 = ''
                tracking_streams = ''
                current_user = self.user.name
                stream_id = self.request.get('url2')
                streams = db.GqlQuery("select * from Streams WHERE stream_url =:1", stream_id)
                for stream_url_ in streams:
                    stream_url2 = stream_url_.stream_url
                for stream_name_ in streams:
                    stream_name2 = stream_name_.stream_name
                for stream_title_ in streams:
                    stream_title2 = stream_title_.stream_title
                for stream_tracking_value_ in streams:
                    stream_tracking_value2 = stream_tracking_value_.tracking_value
                for stream_embedded_stream_ in streams:
                    stream_embedded_stream2 = stream_embedded_stream_.embedded_stream
                tracking_streams = Tracking_Streams(username = self.user.name, stream_url = stream_url2, stream_name = stream_name2, stream_title = stream_title2, tracking_value = 'True', embedded_stream = stream_embedded_stream2)
                tracking_streams.put()
                the_stream = self.request.get('track')
                q = Streams.get_by_id(int(the_stream), parent=None)
                db.delete(q)
                self.redirect('/my_streams/%s' %current_user)
        elif self.request.get('delete_untracked'):
            stream_url2 = ''
            stream_name2 = ''
            stream_title2 = ''
            stream_tracking_value2 = ''
            stream_embedded_stream2 = ''
            tracking_streams = ''
            current_user = self.user.name
            stream_id = self.request.get('url2')
            streams = db.GqlQuery("select * from Streams WHERE stream_url =:1", stream_id)
            for stream_url_ in streams:
                stream_url2 = stream_url_.stream_url
            for stream_name_ in streams:
                stream_name2 = stream_name_.stream_name
            for stream_title_ in streams:
                stream_title2 = stream_title_.stream_title
            for stream_tracking_value_ in streams:
                stream_tracking_value2 = stream_tracking_value_.tracking_value
            for stream_embedded_stream_ in streams:
                stream_embedded_stream2 = stream_embedded_stream_.embedded_stream
            tracking_streams = Tracking_Streams(username = self.user.name, stream_url = stream_url2, stream_name = stream_name2, stream_title = stream_title2, tracking_value = 'True', embedded_stream = stream_embedded_stream2)
            the_stream = self.request.get('delete_untracked')
            q = Streams.get_by_id(int(the_stream), parent=None)
            db.delete(q)
            self.redirect('/my_streams/%s' %current_user)
        elif self.request.get('delete_tracked'):
            stream_url1 = ''
            stream_name1 = ''
            stream_title1 = ''
            stream_tracking_value1 = ''
            stream_embedded_stream1 = ''
            current_user = self.user.name
            stream_id = self.request.get('url')
            tracking_streams = db.GqlQuery("select * from Tracking_Streams WHERE stream_url =:1", stream_id)
            for stream_url_ in tracking_streams:
                stream_url1 = stream_url_.stream_url
            for stream_name_ in tracking_streams:
                stream_name1 = stream_name_.stream_name
            for stream_title_ in tracking_streams:
                stream_title1 = stream_title_.stream_title
            for stream_tracking_value_ in tracking_streams:
                stream_tracking_value1 = stream_tracking_value_.tracking_value
            for stream_embedded_stream_ in tracking_streams:
                stream_embedded_stream1 = stream_embedded_stream_.embedded_stream
            streams = Streams(username = self.user.name, stream_url = stream_url1, stream_name = stream_name1, stream_title = stream_title1, tracking_value = 'False', embedded_stream = stream_embedded_stream1)
            the_stream = self.request.get('delete_tracked')
            q = Tracking_Streams.get_by_id(int(the_stream), parent=None)
            db.delete(q)
            self.redirect('/my_streams/%s' %current_user)


class GetImage(MainHandler):
    def get(self):
        img = db.get(self.request.get("entity_id"))
        self.response.out.write(img.image)

class Gaming_News(MainHandler):
    def get(self):
        current_user = self.user.name
        self.render('gaming_news.html', username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)

class Profile(MainHandler):

    def get(self, profile_id):
        u = User.by_name(profile_id.lower())
        if not u:
            self.redirect('/')
        if self.user and profile_id:
            broadcasttime = ''
            broadcastvar = ''
            games1var = ''
            games2var = ''
            games3var = ''
            key = ''
            team_name = ''
            profile_posts = ''
            current_user = self.user.name
            imgs  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
            imgs2  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
            rating  = db.GqlQuery("select * from Rating WHERE name_of_profile =:1", profile_id).count()
            rating2  = Rating.all()
            profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1 order by date_created desc", profile_id)
            profile_games = db.GqlQuery("select * from Profile_Games WHERE name =:1", profile_id)
            profile_broadcast = db.GqlQuery("select * from Profile_Broadcast WHERE name_of_submitted =:1", profile_id)
            team_name2  = db.GqlQuery("select * from Teams WHERE name =:1", profile_id)
            query2 = db.GqlQuery("SELECT * from Rating WHERE name_of_profile =:1", profile_id)
            for clan in team_name2:
                team_name = clan.team_name_anycase
            for img in imgs:
                key = img.key()
            for games in profile_games:
                games1var = games.game1
            for games in profile_games:
                games2var = games.game2
            for games in profile_games:
                games3var = games.game3
            for broadcast in profile_broadcast:
                broadcastvar = broadcast.broadcast
            for broadcast in profile_broadcast:
                broadcasttime = broadcast.date_created.strftime("%B %d %Y %I:%M:%S")
            if rating != 0:
                sum_me_up = sum(result.rating for result in query2)
                average_rating = (sum_me_up / rating)
            else:
                average_rating = "Not Rated"
            self.render('profile.html', team_name = team_name, rating = average_rating, imgs2 = imgs2, broadcasttime= broadcasttime, broadcastvar = broadcastvar, game1var = games1var, game2var = games2var, game3var = games3var, profile_image = key, profile_id = profile_id, profile_posts = profile_posts, username = self.user.name, profile_username = profile_id, firstname = self.user.first_name, lastname = self.user.last_name, country = self.user.country, month = self.user.month, day = self.user.day, year = self.user.year)

    def post(self, profile_id):
        current_user = self.user.name
        team_name = ''
        profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1", profile_id)
        team_name2  = db.GqlQuery("select * from Teams WHERE name =:1", profile_id)
        for clan in team_name2:
            team_name = clan.team_name_anycase
        if self.request.get('profile_post') != '':
            profile_posts = Profile_Posts (name_of_submitted = self.user.name, name_of_profile = profile_id, name_of_submitted_team = team_name)
            commentupl = self.request.get("profile_post")
            profile_posts.post = (commentupl)
            profile_posts.put()
            self.redirect('/profile/%s' %profile_id)

class Edit_Profile(MainHandler):
    def get(self, profile_id):
        current_user = self.user.name
        profile_posts = ''
        profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1", profile_id)
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", profile_id)
        for clan in team_name:
            team_name = clan.team_name_anycase
        self.render('edit_profile.html', team_name = team_name, profile_posts = profile_posts, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name, country = self.user.country, month = self.user.month, day = self.user.day, year = self.user.year)

class Change_Profile_Image(MainHandler):
    def get(self):
        if self.user:
            key = ''
            imgs  = db.GqlQuery("select * from Profile_Images WHERE name =:1", self.user.name)
            team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
            for clan in team_name:
                team_name = clan.team_name_anycase
            for img in imgs:
                key = img.key()
            self.render('change_profile_image.html', team_name = team_name, profile_image = key, username = self.user.name, email = self.user.email, firstname = self.user.first_name, lastname = self.user.last_name, country = self.user.country)
        else:
            self.redirect('/register')

    def post(self):
        img=''
        img_check = self.request.get('img')
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
        for clan in team_name:
            team_name = clan.team_name_anycase
        if not img_check:
            error = "A profile image has not been selected."
            self.render('change_profile_image.html', team_name = team_name, error_img = error, username = self.user.name, firstname=self.user.first_name, lastname = self.user.last_name)
        else:
            profile_images = Profile_Images(key_name = self.user.name, name = self.user.name)
            imageupl = self.request.get("img")
            profile_images.image = db.Blob(imageupl)
            profile_images.put()
            self.redirect('/profile/%s' %self.user.name)

class Manage_Games(MainHandler):
    def get(self, profile_id):
        current_user = self.user.name
        imgs  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
        profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1", profile_id)
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
        for clan in team_name:
            team_name = clan.team_name_anycase 
        for img in imgs:
            key = img.key()
        self.render('manage_games.html', team_name = team_name, profile_posts = profile_posts, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name, country = self.user.country, month = self.user.month, day = self.user.day, year = self.user.year)
        
    def post(self, profile_id):
        game1 = self.request.get('game1')
        game2 = self.request.get('game2')
        game3 = self.request.get('game3')
        game4 = self.request.get('game4')
        game5 = self.request.get('game5')
        if game1 == "" and game2 == "" and game3 == "":
            profile_games = Profile_Games(key_name = self.user.name, name = self.user.name)
            game1upl = "no_game"
            profile_games.game1 = (game1upl)
            game2upl = "no_game"
            profile_games.game2 = (game2upl)
            game3upl = "no_game"
            profile_games.game3 = (game3upl)
            profile_games.put()
            self.redirect('/profile/%s' %self.user.name)
        elif game1 and game2 == "" and game3 == "":
            profile_games = Profile_Games(key_name = self.user.name, name = self.user.name)
            game1upl = game1
            profile_games.game1 = (game1upl)
            game2upl = "no_game"
            profile_games.game2 = (game2upl)
            game3upl = "no_game"
            profile_games.game3 = (game3upl)
            profile_games.put()
            self.redirect('/profile/%s' %self.user.name)
        elif game1 and game2 and game3 == "":
            profile_games = Profile_Games(key_name = self.user.name, name = self.user.name)
            game1upl = game1
            profile_games.game1 = (game1upl)
            game2upl = game2
            profile_games.game2 = (game2upl)
            game3upl = "no_game"
            profile_games.game3 = (game3upl)
            profile_games.put()
            self.redirect('/profile/%s' %self.user.name)
        elif game1 and game2 and game3:
            profile_games = Profile_Games(key_name = self.user.name, name = self.user.name)
            game1upl = game1
            profile_games.game1 = (game1upl)
            game2upl = game2
            profile_games.game2 = (game2upl)
            game3upl = game3
            profile_games.game3 = (game3upl)
            profile_games.put()
            self.redirect('/profile/%s' %self.user.name)
        elif game1=="" and game2 and game3=="":
            profile_games = Profile_Games(key_name = self.user.name, name = self.user.name)
            game1upl = "no_game"
            profile_games.game1 = (game1upl)
            game2upl = game2
            profile_games.game2 = (game2upl)
            game3upl = "no_game"
            profile_games.game3 = (game3upl)
            profile_games.put()
            self.redirect('/profile/%s' %self.user.name)
        elif game1=="" and game2=="" and game3:
            profile_games = Profile_Games(key_name = self.user.name, name = self.user.name)
            game1upl = "no_game"
            profile_games.game1 = (game1upl)
            game2upl = "no_game"
            profile_games.game2 = (game2upl)
            game3upl = game3
            profile_games.game3 = (game3upl)
            profile_games.put()
            self.redirect('/profile/%s' %self.user.name)
        elif game1=="" and game2 and game3:
            profile_games = Profile_Games(key_name = self.user.name, name = self.user.name)
            game1upl = "no_game"
            profile_games.game1 = (game1upl)
            game2upl = game2
            profile_games.game2 = (game2upl)
            game3upl = game3
            profile_games.game3 = (game3upl)
            profile_games.put()
            self.redirect('/profile/%s' %self.user.name)

        
class Edit_Broadcast(MainHandler):
    def get(self, profile_id):
        current_user = self.user.name
        imgs  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
        profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1", profile_id)
        profile_games = db.GqlQuery("select * from Profile_Games WHERE name =:1", profile_id)
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
        for clan in team_name:
            team_name = clan.team_name_anycase
        for img in imgs:
            key = img.key()
        for games in profile_games:
            games1var = games.game1
        for games in profile_games:
            games2var = games.game2
        for games in profile_games:
            games3var = games.game3
        self.render('edit_broadcast.html', team_name = team_name, game1var = games1var, game2var = games2var, game3var = games3var,profile_image = key, profile_id = profile_id, profile_posts = profile_posts, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name, country = self.user.country, month = self.user.month, day = self.user.day, year = self.user.year)

    def post(self, profile_id):
            profile_broadcast = Profile_Broadcast(key_name = self.user.name, name_of_submitted = self.user.name, name_of_profile = profile_id)
            bcupl = self.request.get("broadcast")
            profile_broadcast.broadcast = (bcupl)
            profile_broadcast.put()
            self.redirect('/profile/%s' %self.user.name)


class Player_Rating(MainHandler):

    def get(self, profile_id):
        broadcasttime = ''
        broadcastvar = ''
        games1var = ''
        games2var = ''
        games3var = ''
        key = ''
        current_user = self.user.name
        imgs  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
        imgs2  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
        rating  = db.GqlQuery("select * from Rating WHERE name_of_profile =:1", profile_id).count()
        rating2  = Rating.all()
        rating_post  = db.GqlQuery("select * from Rating WHERE name_of_profile =:1 order by date_created desc", profile_id)
        profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1 order by date_created desc", profile_id)
        profile_games = db.GqlQuery("select * from Profile_Games WHERE name =:1", profile_id)
        profile_broadcast = db.GqlQuery("select * from Profile_Broadcast WHERE name_of_submitted =:1", profile_id)
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
        for clan in team_name:
            team_name = clan.team_name_anycase
        for img in imgs:
            key = img.key()
        for games in profile_games:
            games1var = games.game1
        for games in profile_games:
            games2var = games.game2
        for games in profile_games:
            games3var = games.game3
        for broadcast in profile_broadcast:
            broadcastvar = broadcast.broadcast
        for broadcast in profile_broadcast:
            broadcasttime = broadcast.date_created.strftime("%B %d %Y %I:%M:%S")
        sum_me_up = sum(result.rating for result in rating2)
        if rating != 0:
            average_rating = (sum_me_up / rating)
        else:
            average_rating = "Not Rated"
        self.render('Player_rating.html', team_name = team_name, count = rating, rating_post = rating_post, rating = average_rating, average_rating = average_rating, imgs2 = imgs2, broadcasttime= broadcasttime, broadcastvar = broadcastvar, game1var = games1var, game2var = games2var, game3var = games3var, profile_image = key, profile_id = profile_id, profile_posts = profile_posts, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name, country = self.user.country, month = self.user.month, day = self.user.day, year = self.user.year)

    def post(self, profile_id):
        current_user = self.user.name
        profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1", profile_id)
        broadcasttime = ''
        broadcastvar = ''
        games1var = ''
        games2var = ''
        games3var = ''
        key = ''
        current_user = self.user.name
        imgs  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
        imgs2  = db.GqlQuery("select * from Profile_Images WHERE name =:1", profile_id)
        rating  = db.GqlQuery("select * from Rating WHERE name_of_profile =:1", profile_id).count()
        rating2  = Rating.all()
        rating_post  = db.GqlQuery("select * from Rating WHERE name_of_profile =:1 order by date_created desc", profile_id)
        profile_posts = db.GqlQuery("select * from Profile_Posts WHERE name_of_profile =:1 order by date_created desc", profile_id)
        profile_games = db.GqlQuery("select * from Profile_Games WHERE name =:1", profile_id)
        profile_broadcast = db.GqlQuery("select * from Profile_Broadcast WHERE name_of_submitted =:1", profile_id)
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
        for clan in team_name:
            team_name = clan.team_name_anycase
        for img in imgs:
            key = img.key()
        for games in profile_games:
            games1var = games.game1
        for games in profile_games:
            games2var = games.game2
        for games in profile_games:
            games3var = games.game3
        for broadcast in profile_broadcast:
            broadcastvar = broadcast.broadcast
        for broadcast in profile_broadcast:
            broadcasttime = broadcast.date_created.strftime("%B %d %Y %I:%M:%S")
        sum_me_up = sum(result.rating for result in rating2)
        if rating != 0:
            average_rating = (sum_me_up / rating)
        else:
            average_rating = "Not Rated"

        if self.request.get('player_rating') == "":
            error = "You must enter at least a rating."
            self.render('Player_rating.html', error = error, team_name = team_name, count = rating, rating_post = rating_post, rating = average_rating, average_rating = average_rating, imgs2 = imgs2, broadcasttime= broadcasttime, broadcastvar = broadcastvar, game1var = games1var, game2var = games2var, game3var = games3var, profile_image = key, profile_id = profile_id, profile_posts = profile_posts, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name, country = self.user.country, month = self.user.month, day = self.user.day, year = self.user.year)
        else:
            rating = Rating (name_of_submitted = self.user.name, name_of_profile = profile_id)
            commentupl = self.request.get("profile_post")
            rating.post = (commentupl)
            ratingupl = self.request.get("player_rating")
            rating.rating = float(ratingupl)
            rating.put()
            self.redirect('/player_rating/%s' %profile_id)

class Create_Team(MainHandler):
    def get(self):
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", self.user.name)
        for clan in team_name:
            team_name = clan.team_name_anycase
        self.render('create_team.html', team_name = team_name, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)

    def post(self):
        team_name = ''
        name = ''
        name1 = ''
        current_user = str(self.user.name)
        team_check = self.request.get('team_name')
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", current_user)
        e = Teams.by_team(team_check.lower())
        for clan in team_name:
            name1 = clan.team_name_anycase
        if not team_check:
            error = "Field is blank."
            self.render('create_team.html', error_team_name = error, team_name = name1, username = self.user.name, firstname=self.user.first_name)
        elif len(team_check) > 14:
            error = "Team name is too long."
            self.render('create_team.html', error_team_name = error, team_name = name1, username = self.user.name, firstname=self.user.first_name)
        elif team_check.find(' ') != -1:
            error = "A team name cannot have spaces."
            self.render('create_team.html', error_team_name = error, team_name = name1, username = self.user.name, firstname=self.user.first_name)
        elif e:
            error = "%s already exists." % (team_check)
            self.render('create_team.html', error_team_name = error, team_name = name1, username = self.user.name, firstname=self.user.first_name)
        else:
            teams = Teams(key_name = self.user.name, name = self.user.name, founder = self.user.name)
            team_from_form = self.request.get("team_name")
            teams.team_name = (team_from_form.lower())
            team_from_form = self.request.get("team_name")
            teams.team_name_anycase = (team_from_form)
            teams.put()
            self.redirect('/profile/%s' %self.user.name)


class Edit_Handle(MainHandler):
    def get(self):
        current_user = self.user.name
        team_name  = db.GqlQuery("select * from Teams WHERE name =:1", current_user)
        for clan in team_name:
            team_name = clan.team_name_anycase
        self.render('edit_handle.html', team_name = team_name, username = self.user.name, firstname = self.user.first_name, lastname = self.user.last_name)


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/register', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/dashboard/(.*)/?', Dashboard),
                               ('/add_stream', Add_Stream),
                               ('/stream_one/(.*)', Stream_One),
                               ('/stream_two/(.*)/(.*)', Stream_Two),
                               ('/stream_three/(.*)/(.*)/(.*)', Stream_Three),
                               ('/stream_four/(.*)/(.*)/(.*)/(.*)', Stream_Four),
                               ('/stream_tracking_list', Stream_Tracking_List),
                               ('/profile/(.*)', Profile),
                               ('/my_streams/(.*)', My_Streams),
                               ('/my_streams_list', My_Streams_List),
                               ('/img/?', GetImage),
                               ('/gaming_news', Gaming_News),
                               ('/edit_profile/(.*)', Edit_Profile),
                               ('/change_profile_image', Change_Profile_Image),
                               ('/manage_games/(.*)', Manage_Games),
                               ('/edit_broadcast/(.*)', Edit_Broadcast),
                               ('/player_rating/(.*)', Player_Rating),
                               ('/create_team', Create_Team),
                               ('/edit_handle', Edit_Handle)],
                              debug=True)
