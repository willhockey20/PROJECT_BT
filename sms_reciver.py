from hashlib import sha1
from flask import Flask, current_app, request, redirect, abort
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.twiml.messaging_response import MessagingResponse
from functools import wraps
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from dotenv import load_dotenv
import hashlib
from sendMsgs import sendUsgNotif
from dataEntryScript import formatMsgJson, genOverviewJson, handleData, handleDataFromJson, handleTurn, initJsonAccount, initNewAccount, jsonIfy, manualOverJson, sendSheetJson, setupSumJson
from dataEntryScript import turnOver
from dataEntryScript import genOverview, sendSheet, changeDate, reHash
import os, threading, time, platform
import schedule
from logging.handlers import TimedRotatingFileHandler

load_dotenv()

def updateCycle():
    while True:
        schedule.run_pending()
        time.sleep(15)

schedule.every().day.at("03:15").do(turnOver)
cycleThread = threading.Thread(target=updateCycle)
cycleThread.start()

PORT_env = os.getenv("port")
app = Flask(__name__)
auth = HTTPBasicAuth()
users = {
    str(os.getenv("usname")):generate_password_hash(os.getenv("pss"))
}


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username
    #print(request.values.get('From', None))
    if request.values.get('From', None) in os.getenv("authNumbers"):
        app.logger.warning("Message Sent from Authorized Number")
    else:
     app.logger.warning("Message sent: Code 401")

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
    sender = hashlib.sha256(request.values.get('From', None).encode('utf-8')).hexdigest()
    resp = MessagingResponse()
    print(hash(sender[1:]))
    if "|" in msg and "Init" not in msg:
        handleDataFromJson(msg, sender)
        body = formatMsgJson(sender)
    elif "Overview" in msg:
        body = genOverviewJson(sender)
    elif "Init" in msg and len(msg) < 6:
        body = "Incorrect Format\n Correct Format: Init : File Name : Billing Date : Budget "
    elif "Init"  in msg:
        temp = msg.split(":")
        body = initJsonAccount(request.values.get('From', None), temp[1][1:], temp[2][1:], temp[3][1:])
    elif "Change Date" in msg.title():
        if len(msg) > 14:
            temp = msg.split(" ")
            newDate = temp[len(temp)-1]
            changeDate(newDate, sender)
            body = "Budget Date Changed to: " + newDate
        else:
            body = "Incorrect Format: Use \"Change Date MM/DD/YY\" "
    elif "Refresh" in msg.title():
        setupSumJson(sender)
        body = "Total spent recalculated: call overview to get an updated value"
    elif "Email" in msg and "@" in msg:
        splits = msg.split(" ")
        addr = ""
        for i in range(len(splits)):
            if "@" in splits[i]:
                addr = splits[i]

        body = sendSheetJson(addr, sender)
    elif "JSON" in msg:
        splits = msg.split(":")
        jsonIfy(request.values.get('From', None)[2:], sender, splits[1])
        body = formatMsgJson(sender) + "\n\n" + genOverviewJson(sender)
    elif "Manual Override" in msg:
        if os.getenv("overrideCode") in msg:
            manualOverJson(sender)
            body = "Cycle override successful"
        else:
            body = "Contact Administrator"
    else:
        body = "Last Purchase: \n" + formatMsgJson(sender)
    resp.message(body)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = PORT_env, debug=True)
