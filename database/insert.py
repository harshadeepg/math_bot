from messenger_bot.logger import log
from database.db_connection import DBConnection
from collections import namedtuple
import ast

db_connection = DBConnection.Instance().get_connection()

user_request = namedtuple('user_request', 'id, query')

user_response = namedtuple('user_response', 'intent, entities, response, sender_id')

user_answer = namedtuple('user_answer', 'sender_id, question_id, answer_id, is_correct, test_id, question_request_id')


def insert_user_request(request_id, request):
    try:
        with db_connection.cursor() as cursor:
            sql = 'INSERT INTO user_request (id, sender_id, query) VALUES (%s, %s, %s)'
            values = parse_request_data(request)
            if values:
                cursor.execute(sql, (request_id, values.id, values.query))
                db_connection.commit()
    except:
        log('Error! insert user request {}'.format(request))


def parse_request_data(request):
    data = ast.literal_eval(request)
    if 'message' in data['entry'][0]['messaging'][0].keys():
        return user_request(
            id=data['entry'][0]['messaging'][0]['sender']['id'],
            query=data['entry'][0]['messaging'][0]['message']['text']
            )


def insert_user_response(response_id, response):
    try:
        with db_connection.cursor() as cursor:
            sql_to_request = 'UPDATE user_request SET intent = %s, entities = %s WHERE id=%s'
            values = parse_response_data(response)
            cursor.execute(sql_to_request, (values.intent, values.entities, response_id))
            sql_to_response = 'INSERT INTO user_response (id, sender_id, response) VALUES (%s, %s, %s)'
            cursor.execute(sql_to_response, (response_id, values.sender_id, values.response))
        db_connection.commit()
    except:
        log('Error! insert user response {}'.format(response))


def parse_response_data(response):
    data = ast.literal_eval(response)
    return user_response(
        intent=data['result']['metadata']['intentName'],
        entities=str(data['result']['parameters']),
        response=data['result']['fulfillment']['speech'],
        sender_id=data['sessionId']
    )


def insert_user_question(response_id, sender_id, question):
    try:
        with db_connection.cursor() as cursor:
            sql = 'INSERT INTO questions_given (id, sender_id, question_id) VALUES (%s, %s, %s)'
            question_id = parse_question(question)
            cursor.execute(sql, (response_id, sender_id, question_id))
        db_connection.commit()
    except:
        log('Error! insert user question {}'.format(question))


def parse_question(question):
    data = ast.literal_eval(question)
    return data['id']


def get_response_id(question_request_id):
    with db_connection.cursor() as cursor:
        sql = 'SELECT id from answer_provided WHERE question_request_id = %s'
        cursor.execute(sql, (question_request_id))
        return cursor.fetchone()['id']


def insert_answer(response_id, values):
    try:
        with db_connection.cursor() as cursor:
            sql = 'INSERT INTO answer_provided (id, sender_id, question_id, answer_id, is_correct, test_id, question_request_id) VALUES (%s, %s, %s, %s, %s, %s, %s)'
            cursor.execute(sql, (
                response_id, values.sender_id,
                values.question_id, values.answer_id,
                values.is_correct, values.test_id,
                values.question_request_id))
        db_connection.commit()
    except:
        log('Error! insert user answer {}'.format(response_id))


def update_answer(response_id, values):
    try:
        with db_connection.cursor() as cursor:
            sql = 'UPDATE answer_provided SET answer_id = %s, is_correct = %s WHERE id = %s'
            cursor.execute(sql, (values.answer_id, values.is_correct, response_id))
        db_connection.commit()
    except:
        log('Error! update user answer {}'.format(response_id))


def is_answer_there(question_request_id):
    with db_connection.cursor() as cursor:
        sql = 'SELECT id FROM answer_provided WHERE question_request_id = %s LIMIT 1'
        cursor.execute(sql, (question_request_id))
        return cursor.fetchone() is not None


def insert_user_answer(response_id, answer):
    try:
        log('insert user {}'.format(answer))
        values = parse_answer(answer)
        if is_answer_there(values.question_request_id):
            update_answer(get_response_id(values.question_request_id), values)
        else:
            insert_answer(response_id, values)
    except:
        log('Error! insert user answer {}'.format(answer))


def parse_answer(answer):
    data = ast.literal_eval(answer)
    if data and 'postback' in data:
        payload = ast.literal_eval(data['postback']['payload'])
        return user_answer(
            sender_id=data['sender']['id'],
            question_id=payload['qid'],
            answer_id=payload['id'],
            is_correct=True if payload['correct'] == payload['id'] else False,
            test_id=payload['test_id'] if 'diagnostic' in payload.keys() and payload['diagnostic'] else None,
            question_request_id=payload['question_request_id']
            )
