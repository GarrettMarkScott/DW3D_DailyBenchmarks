############################# IMPORTING LIBRARIES ##############################
import sqlalchemy as db
import matplotlib as mpl
from matplotlib import style
style.use('dealerworldblue')
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
import configparser
import timeit
import path, os
import codecs
from pandas.plotting import register_matplotlib_converters
pd.plotting.register_matplotlib_converters()


######################## GA SESSION AND EVENT QUERY  ###########################
# Imports 90 days worth of conversational conversions from clients websites

SQL = '''
    SELECT
    	Sessions.dealerID,
    	Sessions.DealerName,
        Sessions.`date`,
        SUM(Sessions.Sessions) AS `Sessions`,
        TotalUniqueGoals.TotalUniqueGoals,
        FormTotals.TotalForms,
        CallTotals.TotalCalls,
        ChatTotals.TotalChats,
        FormTotals.TotalForms/SUM(Sessions.Sessions) AS `FormConversionRate`,
        CallTotals.TotalCalls/SUM(Sessions.Sessions) AS `CallConversionRate`,
        ChatTotals.TotalChats/SUM(Sessions.Sessions) AS `ChatConversionRate`,
        TotalUniqueGoals.TotalUniqueGoals/SUM(Sessions.Sessions) AS `TotalConversionRate`

    FROM data_5d67cfa96d8c0.`GA User Metrics (65)` as Sessions

    LEFT JOIN (
    	SELECT
    		events.DealerID,
    		events.DealerName,
    		SUM(events.`Unique Events`) as TotalForms,
    		events.`date` as EventDay
    	FROM data_5d67cfa96d8c0.`GA Events (64)` AS events
    		WHERE events.TrackedItemName IS NOT NULL
    		AND events.ConversationType = "form"
    		/* AND events.`date` > 20200301 */
    	GROUP BY events.DealerName, events.`date`) AS FormTotals
    ON FormTotals.DealerID = Sessions.DealerID AND FormTotals.EventDay = Sessions.`Date`

    LEFT JOIN (
    	SELECT
    		events.DealerID,
    		events.DealerName,
    		SUM(events.`Unique Events`) as TotalCalls,
    		events.`date` as EventDay
    	FROM data_5d67cfa96d8c0.`GA Events (64)` AS events
    		WHERE events.TrackedItemName IS NOT NULL
    		AND events.ConversationType = "call"
    		/* AND events.`date` > 20200301 */
    	GROUP BY events.DealerName, events.`date`) AS CallTotals
    ON CallTotals.DealerID = Sessions.DealerID AND CallTotals.EventDay = Sessions.`Date`

    LEFT JOIN (
    	SELECT
    		events.DealerID,
    		events.DealerName,
    		SUM(events.`Unique Events`) as TotalUniqueGoals,
    		events.`date` as EventDay
    	FROM data_5d67cfa96d8c0.`GA Events (64)` AS events
    		WHERE events.TrackedItemName IS NOT NULL
    		/* AND events.`date` > 20200301 */
    	GROUP BY events.DealerName, events.`date`) AS TotalUniqueGoals
    ON TotalUniqueGoals.DealerID = Sessions.DealerID AND TotalUniqueGoals.EventDay = Sessions.`Date`

    LEFT JOIN (
    	SELECT
    		events.DealerID,
    		events.DealerName,
    		SUM(events.`Unique Events`) as TotalChats,
    		events.`date` as EventDay
    	FROM data_5d67cfa96d8c0.`GA Events (64)` AS events
    		WHERE events.TrackedItemName IS NOT NULL
    		AND events.ConversationType = "chat"
    		/* AND events.`date` > 20200301 */
    	GROUP BY events.DealerName, events.`date`) AS ChatTotals
    ON ChatTotals.DealerID = Sessions.DealerID AND ChatTotals.EventDay = Sessions.`Date`

    WHERE Sessions.`date` BETWEEN CURDATE() - INTERVAL 13 MONTH AND CURDATE()
    GROUP BY Sessions.DealerID, Sessions.`Date`
    '''

########################  OBTAINING DATABASE CREDENTIALS  ######################
db_config = configparser.ConfigParser()
db_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dwdbconfig.ini')
print("The db ini path is looking here: " + db_ini_path)
db_config.read(db_ini_path)
db_host = db_config['mysql']['host']
db_database = db_config['mysql']['database']
db_user = db_config['mysql']['user']
db_pass = db_config['mysql']['password']
db_port = db_config['mysql']['port']


#################### SETTING SQLALCHEMY CONNECTION #############################
sql_alc_string = 'mysql+pymysql://'+db_user+':'+db_pass+'@'+db_host+':'+db_port+'/'+db_database
print("The SQL Alchemy Call: " + sql_alc_string)
engine = db.create_engine(sql_alc_string)
connection = engine.connect()
metadata = db.MetaData()


############## RETRIEVING SQL GA SESSION AND EVENT DATA TO DATAFRAME ###########

df = pd.read_sql_query(SQL, engine)
df.set_index('Date', inplace = True)
df.index = pd.to_datetime(df.index)
raw_count = len(df.index)
print(raw_count)


##################### OPTIONAL SCATTERPLOT OF DATA ##############################
#plt.figure(figsize=(20,30))
#plt.plot_date(x=df.index, y=df['Sessions']);


##################### OBTAINING STD OF SESSIONS DATA ###########################
session_std = df.std(skipna=True)[0] #The argument calls the second column
print('Session STD: '+str(session_std))
mean = df['Sessions'].mean()
upper = mean+session_std
lower = mean-session_std


############# CREATING SESSIONS DATAFRAME THAT IS 1 STD OF MEAN ################
df_sessions = df[df['Sessions'].between(lower,upper)]
rows_in_1_std = len(df_sessions.index)
print(str(round(rows_in_1_std/raw_count*100,1))+"% of the session data is represented below after excluding data greater than 1 Standard Deviation from the mean")
std_sessions = str(round(rows_in_1_std/raw_count*100,1))

#########  SAVING WEEKLY SESSION AVERAGES TO LOCAL MACHINE #####################
weekly_totals = df_sessions.resample('W').mean()
plt.style.use('dealerworldblue')
#plt.figure(figsize=(20,10))
plt.plot(weekly_totals.index, weekly_totals['Sessions'])
plt.ylabel('Number of Daily Sessions')
plt.xticks(rotation=45)
plt.savefig(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'AvgClientSessions.png'))
plt.cla()


################## OBTAINING STD OF CONVERSION RATE DATA #######################
conv_std = df.std(skipna=True)[8]
mean = df['TotalConversionRate'].mean()
upper = mean+conv_std*2
lower = mean-conv_std*2


########## CREATING CONVERSION RATE DATAFRAME THAT IS 1 STD OF MEAN ############
df_conv = df[df['TotalConversionRate'].between(lower,upper)]
std_instances = len(df_conv.index)
print(str(round(std_instances/raw_count*100,1))+"% of the conversion rate data is represented below after excluding data greater than 2 Standard Deviation from the mean")
std_conversion_rates = str(round(std_instances/raw_count*100,1))


########  SAVING WEEKLY CONVERSION RATE AVERAGES TO LOCAL MACHINE ##############
weeklyrates = []

for client in df_conv['DealerName'].unique():
    temp = df_conv[df_conv['DealerName'] == client]['TotalConversionRate'].resample('W').mean() #NOT STATISTACALLY ACCURATE YET, NEED TO SUM CONVESIONS OVER SESSIONS
    weeklyrates.append(temp)

weeklyrates = pd.concat(weeklyrates)
num_conversion_instances = str(len(weeklyrates))
print('Weekly Rate Instances of Converstion Rate Is: '+num_conversion_instances)

plt.style.use('dealerworldblue')
plt.ylabel('Frequency of Dataset')
plt.hist(weeklyrates.dropna(), bins='auto')
plt.savefig(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ClientConversionRateHistogram.png'))
plt.cla()
######################### SEARCH CONSOLE DATA QUERY ###########################
#Importing SQLalchemy text is used to handle the LIKE statement, without it it does not work.
#There are articles showing this can be done with {} and .format
from sqlalchemy import create_engine, text
SQL = '''
/* OBJECTIVE: Sum of Clicks that were not searching for the dealer by name */
SELECT DISTINCT
    gsc.Date,
    gsc.DealerID,
    gsc.DealerName,
    SUM(gsc.Clicks) AS TotalClicks,
    gsc.`query`,
    gsc.`page` ,
    (CASE
    WHEN (gsc.`query` NOT LIKE CONCAT("%",accounts.dealername,"%") AND gsc.`query` NOT REGEXP CONCAT("^",accounts.`GSCBrandedExclusionRegEx`,"$")) THEN "nonbranded"
    WHEN (gsc.`query` LIKE CONCAT("%",accounts.dealername,"%") OR gsc.`query` REGEXP CONCAT("^",accounts.`GSCBrandedExclusionRegEx`,"$")) THEN "branded"
    ELSE "unknown" END) AS Branded

FROM data_5d67cfa96d8c0.`Google Search Console (70)` AS gsc
JOIN `data_5d67cfa96d8c0`.`Client Accounts (22)` as accounts ON gsc.DealerID = accounts.DealerID
WHERE accounts.`TerminationDate` IS NULL AND gsc.Clicks > 0
GROUP BY gsc.DealerName, gsc.`query`,gsc.`page`

    '''

############## RETRIEVING GOOGLE SEARCH CONSOLE DATA TO DATAFRAME ##############
df_gsc = pd.read_sql_query(text(SQL), engine)
df_gsc.set_index('Date', inplace = True)
df_gsc.index = pd.to_datetime(df_gsc.index)
raw_count = len(df_gsc.index)
df_gsc['TotalClicks'] = df_gsc['TotalClicks'].astype(int)
#df_gsc.sample(10)

################## CLEANING THE GOOGLE SEARCH CONSOLE DATA #####################
#Removing dates before January 1st as there was a very apparent issue in the data collection
gsc_start_date = '2020-01-01' #Note you can select variables in query with @ symbol
df_gsc = df_gsc.query('index >= @gsc_start_date')

#Plots the original data, note that it calls a second image renderb
#plt.figure(figsize=(20,30))
#plt.plot_date(x=df_gsc.index, y=df_gsc['TotalClicks'])

std = df_gsc.std(skipna=True)[0]
mean = df_gsc['TotalClicks'].mean()
upper = mean+std*2
lower = mean-std*2
df_gsc = df_gsc[df_gsc['TotalClicks'].between(lower,upper)]
rows_in_2_std = len(df_gsc.index)
print(str(round(rows_in_2_std/raw_count*100,1))+"% of the search console data is represented below after excluding data greater than 2 Standard Deviation from the mean")
std_gsc = str(round(rows_in_2_std/raw_count*100,1))

#Plots the cleaned data
#plt.figure(figsize=(20,30))
#plt.plot_date(x=df_gsc.index, y=df_gsc['TotalClicks'])


##################### CREATING WEEKLY SEARCH CONSOLE SUMS ######################
weekly_branded_totals = df_gsc.query('Branded == "branded"').resample('W').sum()
weekly_unbranded_totals = df_gsc.query('Branded == "nonbranded"').resample('W').sum()
weekly_unknown_totals = df_gsc.query('Branded == "unknown"').resample('W').sum()


##################### PLOT AND SAVE SEARCH CONSOLE DATA ########################
plt.style.use('dealerworldblue')
plt.xticks(rotation=45)
plt.ylabel('Sum of Weekly Clicks')
plt.plot(weekly_branded_totals.index, weekly_branded_totals['TotalClicks'], label='Branded')
plt.plot(weekly_unbranded_totals.index, weekly_unbranded_totals['TotalClicks'], label='Non-Branded')
plt.plot(weekly_unknown_totals.index, weekly_unknown_totals['TotalClicks'], label='Uknown')
plt.legend()
plt.savefig(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GoogleSearchConsoleTrends.png'))
plt.cla()

##################### READ AND PLOT GOOGLE ADS PERFORMANCE #####################
SQL = """
    SELECT accounts.DealerName, perf.PerformanceScore, perf.`Real CTR` as SearchAdCTR
    FROM `data_5d67cfa96d8c0`.`Account Performance:99` AS perf
    JOIN `data_5d67cfa96d8c0`.`Client Accounts (22)` AS accounts ON perf.DealerId = accounts.DealerID
    """

df = pd.read_sql_query(SQL, engine)
df.sort_values('PerformanceScore', ascending=True, inplace=True)

fig = plt.figure()
plt.barh(width=df.PerformanceScore, y=df.DealerName)
fig.set_size_inches([8,10])
plt.xlabel('Performance Score')
plt.savefig(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GoogleAdsPerformance.png'))
plt.cla()

###################### OBTAINING GMAIL CREDENTIALS #############################
email_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GmailLogin.ini')
print("The email ini path is looking here: " + email_ini_path)
email_config = configparser.ConfigParser()
email_config.read(email_ini_path)
e_user = email_config['Gmail']['user']
e_pass = email_config['Gmail']['password']


############################# SENDING EMAILS ###################################
import smtplib, ssl
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase


msg = MIMEMultipart('alternative')
msg['Subject'] = "Weekly Summary Report"
msg['From'] = e_user
msg['To'] = 'garrettpythontest@gmail.com'


# To add an attachment just add a MIMEBase object to read a picture locally.
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
f.close()

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GoogleSearchConsoleTrends.png'), 'rb') as f:
    # set attachment mime and file name, the image type is png
    mime2 = MIMEBase('image', 'png', filename='GoogleSearchConsoleTrends.png')
    # add required header data:
    mime2.add_header('Content-Disposition', 'attachment', filename='GoogleSearchConsoleTrends.png')
    mime2.add_header('X-Attachment-Id', '1')
    mime2.add_header('Content-ID', '<1>')
    # read attachment file content into the MIMEBase object
    mime2.set_payload(f.read())
    # encode with base64
    encoders.encode_base64(mime2)
    # add MIMEBase object to MIMEMultipart object
    msg.attach(mime2)
f.close()

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ClientConversionRateHistogram.png'), 'rb') as f:
    # set attachment mime and file name, the image type is png
    mime3 = MIMEBase('image', 'png', filename='ClientConversionRateHistogram.png')
    # add required header data:
    mime3.add_header('Content-Disposition', 'attachment', filename='ClientConversionRateHistogram.png')
    mime3.add_header('X-Attachment-Id', '2')
    mime3.add_header('Content-ID', '<2>')
    # read attachment file content into the MIMEBase object
    mime3.set_payload(f.read())
    # encode with base64
    encoders.encode_base64(mime3)
    # add MIMEBase object to MIMEMultipart object
    msg.attach(mime3)
f.close()

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GoogleAdsPerformance.png'), 'rb') as f:
    # set attachment mime and file name, the image type is png
    mime4 = MIMEBase('image', 'png', filename='GoogleAdsPerformance.png')
    # add required header data:
    mime4.add_header('Content-Disposition', 'attachment', filename='GoogleAdsPerformance.png')
    mime4.add_header('X-Attachment-Id', '3')
    mime4.add_header('Content-ID', '<3>')
    # read attachment file content into the MIMEBase object
    mime4.set_payload(f.read())
    # encode with base64
    encoders.encode_base64(mime4)
    # add MIMEBase object to MIMEMultipart object
    msg.attach(mime4)
f.close()


email_content = codecs.open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'email.html'), 'r')
#If format order gets confusing follow this https://www.w3schools.com/python/ref_string_format.asp
email_content = email_content.read().format(std_sessions, std_gsc, num_conversion_instances, std_conversion_rates)
print(email_content)

msg.attach(MIMEText(email_content, 'html', 'utf-8'))



#msg.attach(MIMEText('<html><body><h1>Hello</h1>' +'<img src="cid:0"><img src="cid:1"><img src="cid:2"><img src="cid:3">' +email_content, 'html', 'utf-8'))



email_conn = smtplib.SMTP('smtp.gmail.com',587)
email_conn.ehlo()
email_conn.starttls() #encrypts password, needed for many connections
email_conn.login('garrettmarkscott@gmail.com','mxqhsvwhlwzislxt') #need to generate app password from google
email_conn.sendmail(e_user,'garrettpythontest@gmail.com', msg.as_string())
email_conn.quit()
