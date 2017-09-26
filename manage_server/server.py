#!/usr/bin/env python3
import os
import sys
import json
import time
import tornado.ioloop
import tornado.web
import mysql.connector
from copy import deepcopy
from tornado.httputil import parse_body_arguments
from datetime import datetime
from config import *

bar_info_dict = {
    'home': {
        'title': 'Home',
        'url': '/home',
        'order': 0,
        'type': '',
        'active': False,
    },
    'finance': {
        'title': 'Finance',
        'url': '/finance',
        'order': 1,
        'type': '',
        'active': False,
    },
}


def validate(date_text):
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


class FinanceHandler(tornado.web.RequestHandler):
    def __init__(self, *args):
        super().__init__(*args)
        tmp = deepcopy(bar_info_dict)
        tmp['finance']['active'] = True
        self.bar_info_list = sorted([a for a in tmp.values()], key=lambda x: x['order'])

    def get_record(self, start='', end=''):
        cnx = mysql.connector.connect(user=DB_USERNAME, password=DB_PASSWORD, database=DB_NAME)
        cursor = cnx.cursor()
        v_start = validate(start)
        v_end = validate(end)
        if v_start and v_end:
            query = ('SELECT date, amount, type, remark FROM finance '
                     'WHERE date BETWEEN %s AND %s ORDER BY date ASC')
            cursor.execute(query, (start, end))
        elif v_start:
            query = ('SELECT date, amount, type, remark FROM finance '
                     'WHERE date >= %s ORDER BY date ASC')
            cursor.execute(query, (start,))
        elif v_end:
            query = ('SELECT date, amount, type, remark FROM finance '
                     'WHERE date <= %s ORDER BY date ASC')
            cursor.execute(query, (end,))
        else:
            query = ('SELECT date, amount, type, remark FROM finance '
                     'ORDER BY date ASC')
            cursor.execute(query)

        data = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'amount': float(amount),
                'type': payment_type,
                'remark': remark,
            }
            for (date, amount, payment_type, remark) in cursor
        ]

        cursor.close()
        cnx.close()
        return data

    def add_record(self, request_data):
        cnx = mysql.connector.connect(user=DB_USERNAME, password=DB_PASSWORD, database=DB_NAME)
        cursor = cnx.cursor()
        query = ('INSERT INTO finance '
                 '(date, amount, type, remark) '
                 'VALUES (%s, %s, %s, %s)')
        status = True
        try:
            cursor.execute(query, (request_data['date'], request_data['amount'], request_data['type'], request_data['remark']))
        except Exception as e:
            status = False

        cnx.commit()
        cursor.close()
        cnx.close()
        return status

    def get(self):
        start = self.get_argument('start', '', True)
        end = self.get_argument('end', '', True)

        data = self.get_record(start, end)
        total = int(sum([a['amount'] for a in data]) * 100) / 100.0
        self.render('finance.html', bar_info_list=self.bar_info_list, data=data, status=None, total=total)

    def post(self):
        (args, files) = ({}, {})
        parse_body_arguments('application/x-www-form-urlencoded', self.request.body, args, files)
        request_data = dict([(a, b[0].decode('utf-8')) for (a, b) in args.items()])
        status = None
        if 'date' in request_data and 'amount' in request_data and \
                            'type' in request_data and 'remark' in request_data:
            status = self.add_record(request_data)

        data = self.get_record()
        total = int(sum([a['amount'] for a in data]) * 100) / 100.0
        self.render('finance.html', bar_info_list=self.bar_info_list, data=data, status=status, total=total)


class HomeHandler(tornado.web.RequestHandler):
    def __init__(self, *args):
        super().__init__(*args)
        tmp = deepcopy(bar_info_dict)
        tmp['home']['active'] = True
        self.bar_info_list = sorted([a for a in tmp.values()], key=lambda x: x['order'])

    def get(self):
        self.render('home.html', bar_info_list=self.bar_info_list)


if __name__ == "__main__":
    handler = [
        (r'/home', HomeHandler),
        (r'/finance', FinanceHandler),
    ]
    script_path = os.path.realpath(os.path.dirname(__file__))
    settings = {
        'static_path': os.path.join(script_path, 'static'),
        'template_path': os.path.join(script_path, 'template'),
    }
    dsa_hook_server = tornado.web.Application(handler, **settings)
    dsa_hook_server.listen(SERVER_PORT)
    tornado.ioloop.IOLoop.current().start()
