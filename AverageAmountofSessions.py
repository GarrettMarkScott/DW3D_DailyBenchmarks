############################# IMPORTING LIBRARIES ##############################
import sqlalchemy as db
import matplotlib as mpl
from matplotlib import style
style.use('dealerworldblue')
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import smtplib
import configparser
import timeit
import path, os
import codecs
from pandas.plotting import register_matplotlib_converters
from oauth2client.service_account import ServiceAccountCredentials
import pygsheets
pd.plotting.register_matplotlib_converters()


######################## GA SESSION AND EVENT QUERY  ###########################
# Imports 90 days worth of conversational conversions from clients websites

SQL = '''
    SELECT
    	Sessions.dealerID,
    	Sessions.DealerName,
        Sessions.`date`,
        SUM(Sessions.Sessions) AS `Sessions`,
        COALESCE(FormTotals.TotalForms,0) + COALESCE(CallTotals.TotalCalls,0) + COALESCE(ChatTotals.TotalChats,0) AS `ConversationalConversions`,
        FormTotals.TotalForms,
        CallTotals.TotalCalls,
        ChatTotals.TotalChats,
        (COALESCE(FormTotals.TotalForms,0) + COALESCE(CallTotals.TotalCalls,0) + COALESCE(ChatTotals.TotalChats,0) )/SUM(Sessions.Sessions) AS `TotalConversionRate`,
        FormTotals.TotalForms/SUM(Sessions.Sessions) AS `FormConversionRate`,
        CallTotals.TotalCalls/SUM(Sessions.Sessions) AS `CallConversionRate`,
        ChatTotals.TotalChats/SUM(Sessions.Sessions) AS `ChatConversionRate`

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
    SELECT
        perf.DealerName,
        perf.PerformanceScore,
        perf.`Search Ad CTR` as SearchAdCTR
    FROM `data_5d67cfa96d8c0`.`Account Performance - Don't Modify:99` AS perf
    """

df = pd.read_sql_query(SQL, engine)
df.sort_values('PerformanceScore', ascending=True, inplace=True)

fig = plt.figure()
plt.barh(width=df.PerformanceScore, y=df.DealerName)
fig.set_size_inches([8,10])
plt.xlabel('Performance Score')
plt.savefig(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'GoogleAdsPerformance.png'))
plt.cla()


################### CALCULATING ZSCORES OF CLIENT GROWTH #######################

############### Pulling daily totals from data warehouse #######################
SQL = '''
    SELECT
        leads.DealerID,
        leads.DealerName,
        leads.`Date`,
        leads.Sessions,
        leads.ConversationalConversions,
        leads.TotalForms,
        leads.TotalCalls,
        leads.TotalChats,
        emp.FullName
    FROM `data_5d67cfa96d8c0`.`Total Conversions by Client and Date - CACHED (161)` AS leads
    JOIN `data_5d67cfa96d8c0`.`Client Accounts (22)` AS accounts ON leads.DealerID = accounts.DealerID
    JOIN `data_5d67cfa96d8c0`.`Employees (61)` AS emp ON accounts.PerformanceManagerID = emp.EmployeeID
    WHERE accounts.TerminationDate IS NULL
        '''

sql_alc_string = 'mysql+pymysql://'+db_user+':'+db_pass+'@'+db_host+':'+db_port+'/'+db_database
print("The SQL Alchemy Call: " + sql_alc_string)

db_engine = db.create_engine(sql_alc_string)
db_connection = db_engine.connect()
db_metadata = db.MetaData()

df = pd.read_sql_query(SQL, db_engine)


##################### Cleaning the master dataFrame ###########################

def lookup(s):
    """
    This is an extremely fast approach to datetime parsing.
    For large data, the same dates are often repeated. Rather than
    re-parse these, we store all unique dates, parse them, and
    use a lookup to convert all dates.
    """
    dates = {date:pd.to_datetime(date) for date in s.unique()}
    return s.map(dates)

df['Date'] = lookup(df['Date'])


"""
We now have a dataFrame with formatted dates.
Our plan will be to get the sum aggregates for each dealer
in two different dataFrames. One frame will have the previous 30 day
total of leads. The other will have the previous period. One important
factor to note is that our systems pull the data on a weekly basis so
we will need to factor that in. To deal with this the code subtracts
30 days from the most recent day of data as seen in the code below.
"""

############################# Authorize GSheets ################################

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

"""
Note that you need to go into Google Cloud Services and create a service app to
aquire the json creds. Don't forget to 'enable' google sheets and/or google drive.
You will then need to add the email in the json key to the gsheet with edit permissions.
"""

#Location is explicitly set so that CRON job can be run from the root directory
google_api = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'PersonalGoogleDriveAPICreds.json')
credentials = ServiceAccountCredentials.from_json_keyfile_name(google_api, scope)

gc = pygsheets.authorize(service_file=google_api)

######################### Begin Processing ####################################

def CalculateZScores(IntervalLengths):
    ActiveGSheet = -1
    for IntervalLength in IntervalLengths:
        ActiveGSheet += 1
        LastImportDay = df['Date'].max()
        FirstIntervalDate = LastImportDay - pd.Timedelta(days=IntervalLength*2)


        print("Being processing "+str(IntervalLength)+" day interval")

        #Removes Clients that are not active nor have enough data based on the IntervalLength
        # https://stackoverflow.com/questions/27965295/dropping-rows-from-dataframe-based-on-a-not-in-condition
        print("Last Import Day: "+str(LastImportDay))
        print("Two Intervals ago: "+str(FirstIntervalDate))
        ValidClients = df[df['Date'] <= str(FirstIntervalDate)].groupby('DealerName')['Date'].min().index.tolist()
        df_valid = df[df['DealerName'].isin(ValidClients)]
        #df

        SelectedInterval = (df_valid['Date'] >= LastImportDay - pd.Timedelta(days=IntervalLength))
        PreviousPeriod = (df_valid['Date'] < (df_valid[SelectedInterval]['Date'].min())) & (df_valid['Date'] >= (df_valid[SelectedInterval]['Date'].min() - pd.Timedelta(days=IntervalLength)))

        """
        Great! We now have the last time interval as one dataFrame and the previous
        as another dataFrame. We are going to now reduce each of these dataFrames to their
        sum totals, then merge them back together for difference calculations
        """

        # You'll notice with the way that the code works this report can be ran with different intervals.
        DealerLeads_SelectedInterval = df_valid[SelectedInterval].groupby('DealerName')[['ConversationalConversions','TotalForms','TotalCalls','TotalChats']].sum()
        DealerLeads_PrevPeriod = df_valid[PreviousPeriod].groupby('DealerName')[['ConversationalConversions','TotalForms','TotalCalls','TotalChats']].sum()

        #Renaming the columns since both dataFrames have the same column titles
        DealerLeads_PrevPeriod.columns = ['ConversationalConversions_prev','TotalForms_prev','TotalCalls_prev','TotalChats_prev']


        #Merging the two dataFrames
        df_merged = pd.merge(DealerLeads_SelectedInterval, DealerLeads_PrevPeriod, on='DealerName')

        #Calculating the percentage difference
        df_merged['Calculated Diff'] = (df_merged.ConversationalConversions - df_merged.ConversationalConversions_prev) / df_merged.ConversationalConversions_prev

        #Reducing to needed columns and sorting Values
        df_merged = df_merged[['ConversationalConversions','ConversationalConversions_prev','Calculated Diff']].sort_values(by=['Calculated Diff'], ascending=False)

        #Replacing infinite values from bad data
        df_merged.replace([np.inf, -np.inf], np.nan, inplace=True)

        #Calculating Z-Scores
        mean = df_merged['Calculated Diff'].mean()
        std = df_merged['Calculated Diff'].std()
        print('The mean is: '+str(mean))
        print('The Standard Deviation is: '+str(std))
        df_merged['Z Score'] = (df_merged['Calculated Diff'] - mean) / std


        """
        Because we used a groupby function earlier in our dataFrames we lost the names
        of the performance managers. The code below joins the names back.
        """
        df_final = pd.merge(df_merged, df[['DealerName','FullName']].drop_duplicates(), on='DealerName', how='inner')
        df_final = df_final[df_final['ConversationalConversions_prev'] > 0]


        #This provides the image urls to be placed in our googlesheet for the thumbnails
        PM_Pics = {
            "Mark Ferguson": "https://dealerworldfiles.s3.amazonaws.com/PMs+Profile+Pics/Mark.png",
            "Cassidy Spring": "https://dealerworldfiles.s3.amazonaws.com/PMs+Profile+Pics/Cassidy.jpg",
            "Miranda Milillo": "https://dealerworldfiles.s3.amazonaws.com/PMs+Profile+Pics/Miranda.jpg",
            "Abby Frey": "https://dealerworldfiles.s3.amazonaws.com/PMs+Profile+Pics/Abby.jpg",
            "Troy Spring": "https://dealerworldfiles.s3.amazonaws.com/PMs+Profile+Pics/Troy.png"
        }

        for key in PM_Pics:
                df_final['FullName'].replace(key, '=IMAGE("'+PM_Pics[key]+'")', inplace=True)


        #Remaing columns again to make prettier for end users
        #Note that we change the percentage float to a string with % character
        df_final.columns = ['Dealer Name','Web Leads','Web Leads (Previous Period)','Calculated Diff','Z Score','PM']
        df_final['Calculated Diff'] = df_final['Calculated Diff'].map(lambda n: '{:,.2%}'.format(n))

        print('There are '+str(df_final.count())+' records in this dataFrame')
        print()
        print()
        ############################ Sending to GSheet ################################


        #open the google spreadsheet, [0] selects first sheet
        gsheet = gc.open_by_url('https://docs.google.com/spreadsheets/d/13V8TGGw4z1aEB0hQ-NMLr9GFoBpjTS9RkFOg4Tklrws/edit?usp=sharing')[ActiveGSheet]
        print("PyGSheet Editing Sheet "+str(ActiveGSheet))

        #clear current values in selected range
        gsheet.clear(start = 'B4')

        #update the first sheet with df, (1,1) begins at A1, the first number is verticle starting with 1 (not 0)
        gsheet.set_dataframe(df_final,(3,2))

        #update a single value in the gsheet variable
        gsheet.update_value('B1', "Last Update: "+str(pd.to_datetime('today').date()))




ChosenIntervals = [30,60,90]

CalculateZScores(ChosenIntervals)



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
#email_conn.sendmail(e_user,['garrettpythontest@gmail.com'], msg.as_string())
email_conn.sendmail(e_user,['troyspring@mydealerworld.com','garrettscott@mydealerworld.com','performance@mydealerworld.com'], msg.as_string())
email_conn.quit()
