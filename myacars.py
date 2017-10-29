# coding: utf-8

__version__ = 'git'

import re
import requests
from csv import DictReader
from cStringIO import StringIO
from datetime import datetime
from flask import Flask, request
from flask.logging import DEBUG_LOG_FORMAT
from flask_admin import Admin, AdminIndexView as BaseAdminIndexView
from flask_admin.contrib.sqla import ModelView as BaseModelView
from flask_basicauth import BasicAuth as BaseBasicAuth
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from logging import Formatter, DEBUG
from logging.handlers import RotatingFileHandler

re_log = re.compile(r'(.)(\[[0-9]{2}:[0-9]{2}:[0-9]{2}\])')

app = Flask(__name__)

app.config.update(

    # Flask settings
    SECRET_KEY='dev',  # please set a reasonable SECRET_KEY in config file

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI='sqlite:////tmp/test.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,

    # Flask-BasicAuth settings
    BASIC_AUTH_REALM='myACARS Admin',

    # myACARS settings
    AIRLINE_ICAO='AAA',
    FIRST_NAME='Airline',
    LAST_NAME='Pilot',
    RANK_LEVEL='captain',
    RANK_STRING='Captain',
    USERID='userid',
    PASSWORD='password',
    ENABLE_CHAT=False,
)

app.config.from_envvar('MYACARS_CONFIG', True)

log_handler = RotatingFileHandler('myacars.log', maxBytes=100000,
                                  backupCount=3)
log_handler.setLevel(DEBUG)
log_handler.setFormatter(Formatter(DEBUG_LOG_FORMAT))
app.logger.addHandler(log_handler)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


class BasicAuth(BaseBasicAuth):

    def check_credentials(self, username, password):
        return (username == app.config['USERID'] and
                password == app.config['PASSWORD'])


basic_auth = BasicAuth(app)


class BasicAuthMixin:

    def is_accessible(self):
        return basic_auth.authenticate()

    def inaccessible_callback(self, name, **kwargs):
        return basic_auth.challenge()


class AdminIndexView(BasicAuthMixin, BaseAdminIndexView):
    pass


class ModelView(BasicAuthMixin, BaseModelView):
    pass


class SessionView(ModelView):
    can_create = False
    can_edit = False


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sessionid = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AirportView(ModelView):
    column_searchable_list = ['icao', 'name']
    column_filters = ['icao', 'name', 'country']
    form_excluded_columns = ['flights_from', 'flights_to']


class Airport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    icao = db.Column(db.String(4), nullable=False)
    name = db.Column(db.Unicode(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    country = db.Column(db.String(10), nullable=False)

    def __str__(self):
        return '%s - %s (%s)' % (self.icao, self.name, self.country)


class AircraftView(ModelView):
    column_searchable_list = ['icao', 'name', 'registration']
    column_filters = ['icao', 'name', 'registration']
    form_excluded_columns = ['flights']


class Aircraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    icao = db.Column(db.String(4), nullable=False)
    name = db.Column(db.Unicode(200), nullable=False)
    registration = db.Column(db.String(10), nullable=False)
    max_passengers = db.Column(db.Integer, nullable=False)
    max_cargo = db.Column(db.Integer, nullable=False)

    def __str__(self):
        return '%s - %s (%s)' % (self.registration, self.name, self.icao)


class FlightView(ModelView):
    column_searchable_list = ['airline_icao', 'flight_number']
    column_filters = ['airline_icao', 'flight_number']
    form_excluded_columns = ['duration', 'landing_rate', 'log', 'positions']


class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    airline_icao = db.Column(db.String(4), nullable=False)
    flight_number = db.Column(db.Integer, nullable=False)
    origin_id = db.Column(db.Integer, db.ForeignKey(Airport.id),
                          nullable=False)
    origin = db.relationship('Airport', backref='flights_from',
                             foreign_keys=[origin_id])
    destination_id = db.Column(db.Integer, db.ForeignKey(Airport.id),
                               nullable=False)
    destination = db.relationship('Airport', backref='flights_to',
                                  foreign_keys=[destination_id])
    route = db.Column(db.UnicodeText, nullable=False)
    flight_level = db.Column(db.Integer, nullable=False)
    aircraft_id = db.Column(db.Integer, db.ForeignKey(Aircraft.id),
                            nullable=False)
    aircraft = db.relationship('Aircraft', backref='flights',
                               foreign_keys=[aircraft_id])
    duration = db.Column(db.Integer, nullable=True)
    landing_rate = db.Column(db.Integer, nullable=True)
    log = db.Column(db.UnicodeText, nullable=True)
    comments = db.Column(db.UnicodeText, nullable=True)

    def __str__(self):
        return '%s -> %s' % (self.origin, self.destination)


class PositionView(ModelView):
    can_create = False
    can_edit = False
    can_delete = False


class Position(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey(Flight.id), nullable=False)
    flight = db.relationship('Flight', backref='positions',
                             foreign_keys=[flight_id])
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Integer, nullable=False)
    heading = db.Column(db.Integer, nullable=False)
    ground_speed = db.Column(db.Integer, nullable=False)
    phase = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


admin = Admin(app, name='myACARS', template_mode='bootstrap3',
              index_view=AdminIndexView())
admin.add_view(SessionView(Session, db.session))
admin.add_view(AirportView(Airport, db.session))
admin.add_view(AircraftView(Aircraft, db.session))
admin.add_view(FlightView(Flight, db.session))
admin.add_view(PositionView(Position, db.session))


def build_response(separator, *args):
    return separator.join([unicode(i).replace(separator, u'') for i in args])


def get_response_user():
    return build_response(
        ',',
        '1',                            # dbid
        app.config['AIRLINE_ICAO'],     # code
        '0001',                         # pilotid
        request.args.get('sessionid'),  # sessionid
        app.config['FIRST_NAME'],       # firstname
        app.config['LAST_NAME'],        # lastname
        '',                             # email
        app.config['RANK_LEVEL'],       # ranklevel
        app.config['RANK_STRING'],      # rankstring
    )


@app.route('/smartcars/', methods=['GET', 'POST'])
def smartcars_api():
    app.logger.debug(
        (
            u'\n'
            u'### HEADERS:\n'
            u'%s'
            u'### ARGS:\n'
            u'%s\n'
            u'\n'
            u'### FORM:\n'
            u'%s\n'
        ) % (
            unicode(request.headers).replace('\r', ''),
            request.args,
            request.form,
        )
    )

    action = request.args.get('action')

    if action == 'manuallogin':
        if request.args.get('userid') == app.config['USERID'] and \
           request.form.get('password') == app.config['PASSWORD']:
            sess = Session(sessionid=request.args.get('sessionid'))
            db.session.add(sess)
            db.session.commit()
            return get_response_user()
        return 'AUTH_FAILED'

    elif action == 'automaticlogin':
        if request.args.get('dbid') != '1':
            return 'AUTH_FAILED'
        sess = Session.query.filter_by(
            sessionid=request.args.get('oldsessionid')).first()
        if sess is None:
            return 'AUTH_FAILED'
        sessnew = Session(sessionid=request.args.get('sessionid'))
        db.session.delete(sess)
        db.session.add(sessnew)
        db.session.commit()
        return get_response_user()

    elif action == 'verifysession':
        if not app.config['ENABLE_CHAT']:
            return 'AUTH_FAILED'
        if request.args.get('dbid') != '1':
            return 'AUTH_FAILED'
        sess = Session.query.filter_by(
            sessionid=request.args.get('sessionid')).first()
        if sess is None:
            return 'AUTH_FAILED'
        return build_response(
            ',',
            sess.sessionid,
            app.config['FIRST_NAME'],
            app.config['LAST_NAME'],
        )

    elif action == 'getpilotcenterdata':
        if request.args.get('dbid') != '1':
            return 'AUTH_FAILED'
        return build_response(
            ',',
            '00:00:00',
            '0',
            '-100',
            '0',
        )

    elif action == 'getairports':
        airports = []
        qs = Airport.query.all()
        if qs:
            for apt in Airport.query.all():
                airports.append(
                    build_response(
                        '|',
                        apt.id,
                        apt.icao.upper(),
                        apt.name,
                        apt.latitude,
                        apt.longitude,
                        apt.country,
                    )
                )
        else:
            return 'NO_DATA'
        return build_response(
            ';',
            *airports
        )

    elif action == 'getaircraft':
        aircrafts = []
        qs = Aircraft.query.all()
        for acf in qs:
            aircrafts.append(
                build_response(
                    ',',
                    acf.id,
                    acf.name,
                    acf.icao,
                    acf.registration,
                    acf.max_passengers,
                    acf.max_cargo,
                    app.config['RANK_LEVEL'],
                )
            )
        return build_response(
            ';',
            *aircrafts
        )

    elif action == 'getbidflights':
        flights = []
        qs = Flight.query.all()
        if qs:
            for flt in Flight.query.all():
                flights.append(
                    build_response(
                        '|',
                        flt.id,
                        flt.id,
                        flt.airline_icao,
                        flt.flight_number,
                        flt.origin.icao,
                        flt.destination.icao,
                        flt.route,
                        flt.flight_level * 100,
                        flt.aircraft_id,
                        'N/A',
                        'N/A',
                        'N/A',
                        'randomopen',
                        '',
                        '',
                    )
                )
        else:
            return 'NONE'
        return build_response(
            ';',
            *flights
        )

    elif action == 'positionreport':
        if request.args.get('dbid') != '1':
            return 'AUTH_FAILED'
        sess = Session.query.filter_by(
            sessionid=request.args.get('sessionid')).first()
        if sess is None:
            return 'AUTH_FAILED'
        flt = Flight.query.get(int(request.args.get('bidid')))
        if flt is None:
            return 'ERROR'
        route = request.form.get('route')
        if route is not None and route != flt.route:
            flt.route = route

        lat = float(request.args.get('latitude', '0').replace(',', '.'))
        lon = float(request.args.get('longitude', '0').replace(',', '.'))

        if lon < 0.005 and lon > -0.005:
            lon = 0

        if lat < 0.005 and lat > -0.005:
            lat = 0

        pos = Position(
            flight=flt,
            latitude=lat,
            longitude=lon,
            altitude=int(request.args.get('altitude', 0)),
            heading=int(request.args.get('magneticheading', 0)),
            ground_speed=int(request.args.get('groundspeed', 0)),
            phase=int(request.args.get('phase', 0)),
        )
        db.session.add(pos)
        db.session.commit()
        return 'SUCCESS'

    elif action == 'filepirep':
        if request.args.get('dbid') != '1':
            return 'AUTH_FAILED'
        sess = Session.query.filter_by(
            sessionid=request.args.get('sessionid')).first()
        if sess is None:
            return 'AUTH_FAILED'
        flt = Flight.query.get(int(request.args.get('bidid')))
        if flt is None:
            return 'ERROR'
        route = request.form.get('route')
        if route is not None and route != flt.route:
            flt.route = route
        flt.log = re_log.sub(r'\1\n\2', request.form.get('log', ''))
        flt.comments = request.form.get('comments')
        flt.landing_rate = int(request.args.get('landingrate', 0))
        time = datetime.strptime(request.args.get('flighttime', '00.00'),
                                 '%H.%M').time()
        flt.duration = time.minute + (60 * time.hour)
        db.session.commit()
        return 'SUCCESS'

    # The following actions are not supported by myACARS

    elif action == 'bidonflight':
        return 'AUTH_FAILED'

    elif action == 'deletebidflight':
        return 'AUTH_FAILED'

    elif action == 'searchpireps':
        return 'NONE'

    elif action == 'getpirepdata':
        return ''

    elif action == 'searchflights':
        return 'NONE'

    elif action == 'createflight':
        return 'AUTH_FAILED'

    return (
        'Script OK, Frame Version: myACARS/%s, Interface Version: myACARS/%s'
        % (__version__, __version__)
    )


@manager.command
def populate_airports():
    '''Load (large and medium) airports from ourairports.com'''
    resp = requests.get('http://ourairports.com/data/airports.csv')
    resp.raise_for_status()

    reader = DictReader(StringIO(resp.content))
    for line in reader:
        if not line['gps_code']:
            continue
        if len(line['gps_code']) > 4:
            raise RuntimeError('Invalid ICAO: %s' % line['gps_code'])
        if line['type'] not in ('medium_airport', 'large_airport'):
            continue
        print line['gps_code'], '-', line['name']
        apt = Airport.query.filter_by(icao=line['gps_code']).first()
        create_apt = apt is None
        if create_apt:
            apt = Airport(icao=line['gps_code'])
        apt.name = line['name'].decode('utf-8')
        apt.latitude = line['latitude_deg']
        apt.longitude = line['longitude_deg']
        apt.country = line['iso_country']
        if create_apt:
            db.session.add(apt)
    db.session.commit()


if __name__ == '__main__':
    manager.run()
