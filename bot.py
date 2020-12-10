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

def get_lesson_num(t):
    if t <= 9*60 + 15:
        return 0
    elif t <= 10*60 + 10:
        return 1
    elif t <= 11*60 + 15:
        return 2
    elif t <= 12*60 + 20:
        return 3
    elif t <= 13*60 + 15:
        return 4
    elif t <= 14*60 + 20:
        return 5
    elif t <= 15*60 + 25:
        return 6
    else:
        return -1

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
wk = gc.open_by_key(credentials["sheet_id"])[0]
tt = gc.open_by_key(credentials["timetable_id"])[0]

tz = pytz.timezone('Europe/Moscow')
allCells = wk.range(wk.cell((1, 1)).label + ':' + wk.cell((wk.rows, wk.cols)).label)

result, data = mail.uid('search', None, "ALL")
last_uid = data[0].split()[-1]
now = datetime.now(tz)
currLessonNum = get_lesson_num(now.hour*60 + now.minute)
if currLessonNum == -1:
    lesson = "null"
else:        
    lesson = tt.cell((currLessonNum+1, now.weekday()+1)).value
for r in allCells:
    for c in r:
        c.color = (1.0, 1.0, 1.0, 1.0)
if lesson != "null":
    for row, uid in enumerate(wk.get_col(5)):
        if uid == lesson:
            r = wk.range(wk.cell((row+1, 1)).label + ':' + wk.cell((row+1, wk.cols)).label)[0]
            for c in r:
                c.color = (0.57, 0.79, 0.47, 1.0)
lastLessonNum = currLessonNum
print('Ready!')
print('Waiting...')
time.sleep(60)

while True:
    print('Checking...')
    now = datetime.now(tz)
    currLessonNum = get_lesson_num(now.hour*60 + now.minute)
    if currLessonNum != lastLessonNum:
        if currLessonNum == -1:
            lesson = "null"
        else:        
            lesson = tt.cell((currLessonNum+1, now.weekday()+1)).value
        for r in allCells:
            for c in r:
                c.color = (1.0, 1.0, 1.0, 1.0)
        if lesson != "null":
            for row, uid in enumerate(wk.get_col(5)):
                if uid == lesson:
                    r = wk.range(wk.cell((row+1, 1)).label + ':' + wk.cell((row+1, wk.cols)).label)[0]
                    for c in r:
                        c.color = (0.57, 0.79, 0.47, 1.0)
        lastLessonNum = currLessonNum
    try:
        result, data = mail.uid('search', None, "ALL")
        uidList = data[0].split()
        curr_uid = uidList[-1]
        if curr_uid != last_uid:
            try:
                start_index = uidList.index(last_uid)
            except ValueError:
                start_index = len(uidList) - 1
                while last_uid < uidList[start_index]:
                    start_index -= 1
            for i in range(start_index + 1, len(uidList)):
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
