import imaplib
import email
import email.message
import pygsheets # external
import time
from datetime import datetime
import pytz # external
import json
import re
import tldextract # external

def get_text(email_message_instance):
    res = ""
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                chset = part.get_content_charset()
                res += part.get_payload(decode=True).decode(chset)
    elif maintype == 'text':
        chset = email_message_instance.get_content_charset()
        res+= email_message_instance.get_payload(decode=True).decode(chset)
    return res

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
time.sleep(60)

while True:
    print('Checking...')
    try:
        result, data = mail.uid('search', None, "ALL")
        uidList = data[0].split()
        curr_uid = uidList[-1]
        if curr_uid != last_uid:
            start_index = uidList.index(last_uid) + 1
            if start_index == -1:
                i = len(uidList) - 1
                while last_uid < uidList[i]:
                    i -= 1
                start_index = i + 1
            for i in range(start_index, len(uidList)):
                result, data = mail.uid('fetch', uidList[i], '(RFC822)')
                raw_email = data[0][1]
                email_message = email.message_from_bytes(raw_email)
                from_addr = email.utils.parseaddr(email_message['From'])[1]
                contents = get_text(email_message)
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
                            wk.cell((row+1, 3)).set_value(datetime.now(tz).strftime("%H:%M %b-%d"))
            last_uid = curr_uid
    except imaplib.IMAP4.abort:
        mail = imaplib.IMAP4_SSL("imap.mail.ru")
        mail.login(credentials["login"], credentials["password"])
        mail.select('INBOX')
        continue
                    
    print('Waiting...')
    now = datetime.now(tz)
    hrs = now.hour
    wd = now.weekday()
    if wd == 6:
        time.sleep((24-hrs)*3600)
    elif hrs >= 16 and hrs < 22:
        time.sleep(3600)
    elif hrs >= 22:
        time.sleep((30-hrs)*3600)
    elif hrs <= 5:
        time.sleep((6-hrs)*3600)
    else:
        time.sleep(60)
