from flask import Flask, current_app, request, redirect, abort
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.twiml.messaging_response import MessagingResponse
from functools import wraps
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
from dataEntryScript import handleData
from dataEntryScript import formatMsg

import os

load_dotenv()
PORT_env = os.getenv("port")
app = Flask(__name__)
auth = HTTPBasicAuth()
users = {
    "willryan":generate_password_hash(os.getenv("pss"))
}

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

def validate_t_request(f):
    @wraps(f)
    def decorated_fn(*args, **kwargs):
        validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))

        valid_req = validator.validate(request.url, request.form, request.headers.get('X-TWILIO-SIGNATURE', ''))
        if valid_req or current_app.debug:
            return f(*args, **kwargs)
        else:
            return abort(403)

    return decorated_fn

@app.route("/sms", methods=['GET', 'POST'])
@validate_t_request
@auth.login_required
def sms_reply():

    msg = request.values.get('Body', None)

    resp = MessagingResponse()
    handleData(msg)
    sender = request.values('From')
    print(str(sender))
    body = formatMsg()
    resp.message(body)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = PORT_env, debug=True)

