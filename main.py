# -*- coding: utf-8 -*-
from irclogparser import LogParser
import os
import re

DATA_DIR = 'data'
USE_DB = False
if USE_DB:
    import psycopg2cffi as psycopg2
    from psycopg2cffi.extensions import QuotedString

out = open('ubuntu.sql', 'w')
id = 1

lone = re.compile(
    ur'''(?x)            # verbose expression (allows comments)
    (                    # begin group
    [\ud800-\udbff]      #   match leading surrogate
    (?![\udc00-\udfff])  #   but only if not followed by trailing surrogate
    )                    # end group
    |                    #  OR
    (                    # begin group
    (?<![\ud800-\udbff]) #   if not preceded by leading surrogate
    [\udc00-\udfff]      #   match trailing surrogate
    )                    # end group
    ''')

def get_date(s):
    return s[5:15]

def qs(s):
    return QuotedString(s.encode('utf-8')).getquoted()

def commit(con, date, time, sender, recipient, message):
    global id
    YYYY = int(date[:4])
    MM = int(date[5:7])
    DD = int(date[8:])
    hh = int(time[:2])
    mm = int(time[3:])
    if USE_DB:
        dt = psycopg2.Timestamp(YYYY, MM, DD, hh, mm, 00)
        cur = con.cursor()
        sql = f"""INSERT INTO messages (timestamp, sender, recipient, message) VALUES ({dt}, {qs(sender)}, {qs(recipient) if recipient else "''"}, {qs(message)})"""
        con.cursor().execute(sql)
    else:
        dt = "%d-%d-%d %d:%d:00" % (YYYY, MM, DD, hh, mm)
        s = "%d\t%s\t%s\t%s\t%s\t" % (id, dt, sender, recipient if recipient else '', message)
        s = s.replace('\\', '\\\\') + "\\N\n"
        s = lone.sub(ur'\ufffd', s).encode('utf8')
        out.write(s)
        id += 1

def main():
    con = psycopg2.connect(database='ubuntu') if USE_DB else None
    fnames = os.listdir(DATA_DIR)
    nicks = set()
    prev_nicks = set()
#    fnames = ['2004-09-27-#ubuntu.txt', '2004-09-17-#ubuntu.txt', '2007-10-17-#ubuntu.txt', '2012-01-18-#ubuntu.txt']
    for fname in fnames:
        fname = "%s/%s" % (DATA_DIR, fname)
        print fname
        date = get_date(fname)
        with open(fname, 'r') as f:
            lp = LogParser(f)
            lp.prev_nicks = prev_nicks
            for time, what, info in lp:
                if what == LogParser.COMMENT:
                    commit(con, date, time, info[0], info[1], info[2])
            nicks = nicks.union(lp.nicks)
            prev_nicks = lp.nicks
    with open('nicks.txt', 'w') as f:
        for nick in nicks:
            f.write('%s\n' % nick)

    if USE_DB:
        con.commit()

if __name__ == '__main__':
    main()
