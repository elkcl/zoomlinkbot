import imaplib
import email
import email.message
import pygsheets # external
import time
from datetime import datetime
import pytz # external
import json
import base64
import re
import tldextract # external

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
mail.login(credentials["login"], credentials["password"])
mail.select('INBOX')

gc = pygsheets.authorize(service_file='serviceacc.json')
sh = gc.open_by_key(credentials["sheet_id"])
wk = sh[0]

tz = pytz.timezone('Europe/Moscow')

result, data = mail.uid('search', None, "ALL")
last_uid = data[0].split()[-1]
print('Ready!')
print('Waiting...')
time.sleep(300)

while True:
    print('Checking...')
    result, data = mail.uid('search', None, "ALL")
    uidList = data[0].split()
    curr_uid = uidList[-1]
    if curr_uid != last_uid:
        start_index = uidList.index(last_uid)
        if start_index == -1:
            start_index = len(uidList) - 1
        last_uid = curr_uid
        for i in range(start_index, len(uidList)):
            result, data = mail.uid('fetch', uidList[i], '(RFC822)')
            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)
            from_addr = email.utils.parseaddr(email_message['From'])[1]
            contents = base64.b64decode(get_first_text_block(email_message)).decode('utf-8')
            urls = re.findall(r'(https?://[^\s]+)', contents)
            zoom_link = ""
            found = False
            for url in urls:
                ex = tldextract.extract(url)
                if ex.domain == 'zoom' and ex.suffix == 'us':
                    zoom_link = url
                    found = True
                    break
            if found:
                print('Found!')
                for row, addrs in enumerate(wk.get_col(4)):
                    if addrs.find(from_addr) != -1:
                        wk.cell((row+1, 2)).set_value(zoom_link)
                        wk.cell((row+1, 3)).set_value(datetime.now(tz).strftime("%H:%M %b-%y"))
                        break
                    
    print('Waiting...')
    time.sleep(300)
