#!/usr/bin/env python
# coding: utf-8

# In[179]:


import sqlalchemy as db
import matplotlib as mpl
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
import configparser


# In[180]:


SQL = '''
    SELECT
        date,
        SUM(sessions) as 'Sessions',
        DealerName
    FROM `data_5d67cfa96d8c0`.`GA User Metrics (65)` AS sessions
    GROUP BY Date, DealerName
    ORDER BY Date DESC
    '''


# In[181]:


db_config = configparser.ConfigParser()
db_config.read('dwdbconfig.ini')
db_host = db_config['mysql']['host']
db_database = db_config['mysql']['database']
db_user = db_config['mysql']['user']
db_pass = db_config['mysql']['password']
db_port = db_config['mysql']['port']


# In[182]:


sql_alc_string = 'mysql+pymysql://'+db_user+':'+db_pass+'@'+db_host+':'+db_port+'/'+db_database
print(sql_alc_string)


# In[183]:


engine = db.create_engine(sql_alc_string)


# In[184]:


connection = engine.connect()
metadata = db.MetaData()


# In[185]:


df = pd.read_sql_query(SQL, engine)
df.set_index('Date', inplace = True)
df.index = pd.to_datetime(df.index)
raw_count = len(df.index)
print(raw_count)


# In[186]:


df


# In[187]:


plt.figure(figsize=(20,30))
plt.plot_date(x=df.index, y=df['Sessions']);


# In[188]:


std = df.std(skipna=True)[0]
mean = df['Sessions'].mean()
upper = mean+std
lower = mean-std


# In[189]:


df = df[df['Sessions'].between(lower,upper)]
rows_in_1_std = len(df.index)
print(str(round(rows_in_1_std/raw_count*100,1))+"% of the data is represented below after excluding data greater than 1 Standard Deviation from the mean")


# In[190]:


#What the "Clean Data" Looks like
plt.figure(figsize=(20,30))
plt.plot_date(x=df.index, y=df['Sessions']);


# In[191]:


weekly_totals = df.resample('W').mean()


# In[192]:


plt.figure(figsize=(20,10))
plt.plot(weekly_totals.index, weekly_totals['Sessions'])
plt.xlabel('Date')
plt.ylabel('Daily Average Sessions')
plt.savefig('AvgClientSessions.png')


# In[193]:


#securing password use GmailLogin.ini
email_config = configparser.ConfigParser()
email_config.read('GmailLogin.ini')
e_user = email_config['Gmail']['user']
e_pass = email_config['Gmail']['password']
#print(type(e_user))


# In[195]:


import smtplib, ssl
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase


# In[196]:


msg = MIMEMultipart('alternative')
msg['Subject'] = "Average Daily Sessions"
msg['From'] = e_user
msg['To'] = 'garrettscott@mydealerworld.com'

msg_content = MIMEText('This might be the one 2', 'plain', 'utf-8')
msg.attach(msg_content)


# to add an attachment is just add a MIMEBase object to read a picture locally.
with open('AvgClientSessions.png', 'rb') as f:
    # set attachment mime and file name, the image type is png
    mime = MIMEBase('image', 'png', filename='AvgClientSessions.png')
    # add required header data:
    mime.add_header('Content-Disposition', 'attachment', filename='AvgClientSessions.png')
    mime.add_header('X-Attachment-Id', '0')
    mime.add_header('Content-ID', '<0>')
    # read attachment file content into the MIMEBase object
    mime.set_payload(f.read())
    # encode with base64
    encoders.encode_base64(mime)
    # add MIMEBase object to MIMEMultipart object
    msg.attach(mime)

msg.attach(MIMEText('<html><body><h1>Hello</h1>' +'<p><img src="cid:0"></p>' + '</body></html>', 'html', 'utf-8'))

email_conn = smtplib.SMTP('smtp.gmail.com',587)
email_conn.ehlo()
email_conn.starttls() #encrypts password, needed for many connections
email_conn.login('garrettmarkscott@gmail.com','mxqhsvwhlwzislxt') #need to generate app password from google
email_conn.sendmail(e_user,'garrettscott@mydealerworld.com', msg.as_string())
email_conn.quit()
# server = smtplib.SMTP(smtp_server, 25)
# server.set_debuglevel(1)
# server.login(from_addr, password)
# server.sendmail(from_addr, [to_addr], msg.as_string())
# server.quit()


# In[197]:





# In[ ]:





# In[ ]:
