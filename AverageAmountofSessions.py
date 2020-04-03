
import sqlalchemy as db
import matplotlib as mpl
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
import configparser
import path, os
from pandas.plotting import register_matplotlib_converters



pd.plotting.register_matplotlib_converters()


SQL = '''
    SELECT
        date,
        SUM(sessions) as 'Sessions',
        DealerName
    FROM `data_5d67cfa96d8c0`.`GA User Metrics (65)` AS sessions
    GROUP BY Date, DealerName
    ORDER BY Date DESC
    '''


db_config = configparser.ConfigParser()
db_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dwdbconfig.ini')
print("The db ini path is looking here: " + db_ini_path)
db_config.read(db_ini_path)
db_host = db_config['mysql']['host']
db_database = db_config['mysql']['database']
db_user = db_config['mysql']['user']
db_pass = db_config['mysql']['password']
db_port = db_config['mysql']['port']



sql_alc_string = 'mysql+pymysql://'+db_user+':'+db_pass+'@'+db_host+':'+db_port+'/'+db_database
print(sql_alc_string)



engine = db.create_engine(sql_alc_string)



connection = engine.connect()
metadata = db.MetaData()



df = pd.read_sql_query(SQL, engine)
df.set_index('Date', inplace = True)
df.index = pd.to_datetime(df.index)
raw_count = len(df.index)
print(raw_count)


plt.figure(figsize=(20,30))
plt.plot_date(x=df.index, y=df['Sessions']);


std = df.std(skipna=True)[0]
mean = df['Sessions'].mean()
upper = mean+std
lower = mean-std


df = df[df['Sessions'].between(lower,upper)]
rows_in_1_std = len(df.index)
print(str(round(rows_in_1_std/raw_count*100,1))+"% of the data is represented below after excluding data greater than 1 Standard Deviation from the mean")


weekly_totals = df.resample('W').mean()

#Saving Weekly Session Averages to Local Machine
plt.figure(figsize=(20,10))
plt.plot(weekly_totals.index, weekly_totals['Sessions'])
plt.xlabel('Date')
plt.ylabel('Daily Average Sessions')
plt.savefig(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'AvgClientSessions.png'))

#Importing gmail credentials using GmailLogin.ini

email_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GmailLogin.ini')
print("The email ini path is looking here: " + email_ini_path)
email_config = configparser.ConfigParser()
email_config.read(email_ini_path)
e_user = email_config['Gmail']['user']
e_pass = email_config['Gmail']['password']


#Importing and sending email
import smtplib, ssl
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase


msg = MIMEMultipart('alternative')
msg['Subject'] = "Weekly Summary Report"
msg['From'] = e_user
msg['To'] = 'garrettpythontest@gmail.com'


# To add an attachment is just add a MIMEBase object to read a picture locally.
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'AvgClientSessions.png'), 'rb') as f:
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
email_conn.sendmail(e_user,'garrettpythontest@gmail.com', msg.as_string())
email_conn.quit()
