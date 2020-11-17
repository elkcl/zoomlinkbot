import imaplib
import email
import email.message
import pygsheets
import time
import json
import base64

def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return email_message_instance.get_payload()

with open("credentials.json", "r") as read_file:
    credentials = json.load(read_file)
mail = imaplib.IMAP4_SSL("imap.mail.ru")
mail.login(credentials.login, credentials.password)
mail.select('INBOX')

gc = pygsheets.authorize(service_file='serviceacc.json')
sh = gc.open_by_key("13chRJHm9AJ9TOTmbUw04AAhv5mv5FojM2DaepFPN19c")
wk = sh[0]

last_uid = ""

while True:
    result, data = mail.uid('search', None, "ALL")
    curr_uid = data[0].split()[-1]
    if curr_uid != lastuid:
        last_uid = curr_uid
        result, data = mail.uid('fetch', curr_uid, '(RFC822)')
        raw_email = data[0][1]
        email_message = email.message_from_bytes(raw_email)
        from_addr = email.utils.parseaddr(email_message['From'])[1]
        contents = base64.b64decode(get_first_text_block(email_message)).decode('utf-8')
        if contents.find("zoom.us") != -1:
            #do stuff
    
    time.sleep(300)
