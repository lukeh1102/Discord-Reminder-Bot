import datetime
import os
import schedule
import asyncio
from dotenv import load_dotenv

import discord
from discord.utils import find
from discord.ext import commands, tasks

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
serverList = []

@tasks.loop(hours=24)
async def checkForReminders():
    #get events happening today for every calendar
    guilds = client.guilds
    for guild in guilds:
        for x in calendar_list['items']:
            if str(x['summary']) == str(guild.name):
                calId = x['id']
                print(calId)

        #get events happening today
        now = datetime.datetime.now().isoformat()
        now=now[:19] + "-05:00"
        nowTomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        nowTomorrow=nowTomorrow[:19] + "-05:00"
        events = service.events().list(calendarId=calId, timeMin=now, timeMax=nowTomorrow ).execute()
        events = events.get('items', [])
        if not events:
            print('No upcoming events found.')
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(start, event['summary'])
                #send message to channel
                channel = find(lambda c: c.name == 'reminders', guild.channels)
                channel = client.get_channel(channel.id)
                if channel is not None:
                    await channel.send('REMINDER: ' + event['summary'] + " Due " + start[:10] + " " + start[11:16])

@checkForReminders.before_loop
async def before_my_task():
    hour = 9
    minute = 0
    now = datetime.datetime.now()
    future = datetime.datetime(now.year, now.month, now.day, hour, minute)
    if now.hour >= hour and now.minute > minute:
        future += datetime.timedelta(days=1)
    await asyncio.sleep((future-now).seconds)



creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
            token.write(creds.to_json())

try:
    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.now().isoformat()
    print("CST Time: " + str(now))


    #Printing the list of calenders
    calendar_list = service.calendarList().list().execute()
    print()
    for x in calendar_list['items']:
        print(x['summary'])
        print(x['id'])
        print()

except HttpError as error:
    print('An error occurred: %s' % error)



@client.event
async def on_ready():
    print('Discord bot logging in as ' + str(client.user))
    print('Discord bot ID: ' + str(client.user.id))
    for server in client.guilds:
        print(serverList.append(server.name))
    print('Discord bot present in ' + str(serverList))
    print('Discord bot is ready to go!')
    checkForReminders.start()

@client.event
async def on_guild_join(guild):
    guildName = str(guild.name)

    #Create calender for server
    calendar = {'summary': guildName, 'timeZone': 'America/Chicago'}
    created_calendar = service.calendars().insert(body=calendar).execute()
    print("Calendar created: " + str(created_calendar['id']))

    #create reminders channel if not already created
    channel = find(lambda c: c.name == 'reminders', guild.channels)
    if channel is None:
        await guild.create_text_channel('reminders')


    #Say Hello
    print("Joined server " + guildName)
    reminders = find(lambda x: x.name == 'reminders',  guild.text_channels)
    if reminders and reminders.permissions_for(guild.me).send_messages:
        await reminders.send('Hello {}, I\'m here to help keep track of reminders! type $help for the list of commands'.format(guild.name))


@client.event
async def on_message(message):
    #ignore messages from the bot
    if message.author == client.user:
        return

    #ignore messages not in the reminders channel
    if message.channel.name != 'reminders':
        return
    
    #create new calender
    if message.content.startswith('$createcalender'):
        #Message Format: $createcalender <calenderName>
        calendar = {'summary': str(message.guild.name), 'timeZone': 'America/Chicago'}
        created_calendar = service.calendars().insert(body=calendar).execute()
        print("Calendar created: " + str(created_calendar['id']))
        await message.channel.send("Calendar created: " + str(message.guild.name))

    #list bot commands
    if message.content.startswith('$help'):
        await message.channel.send("List of commands: \n$createcalender <calenderName> - Creates a new calender for the server \n$createreminder <reminderName> <YYYY-MM-DD> <HH:MM>(24-Hour Format) - Adds a reminder to the calender \n$changereminder <reminderName> <YYYY-MM-DD> <HH:MM>  - Changes the date and time of a reminder \n$listreminders - Lists all reminders in the calender\n$deletereminder <reminderName> - Deletes a reminder from the calender")

    #create new reminder
    if message.content.startswith('$createreminder'):
        #Message Format: $createreminder <reminderName> <YYYY-MM-DD> <HH:MM>
        for x in calendar_list['items']:
            if str(x['summary']) == str(message.guild.name):
                calId = x['id']
                print(calId)
                break

        
        wordList = message.content.split()
        reminderName = wordList[1]
        reminderDate = wordList[2]
        reminderTime = wordList[3]
        print(wordList)
        
        event = {'summary': reminderName, 
                'start': {'dateTime': reminderDate + "T" + reminderTime + ":00-05:00"},
                'end': {'dateTime': reminderDate + "T" + reminderTime +  ":59-05:00"},
                
                }
        print(event)
                

        event = service.events().insert(calendarId=calId, body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))
        
        await message.channel.send('Reminder Created')

    #delete reminder
    if message.content.startswith('$deletereminder'):
        #Message Format: $deletereminder <reminderName>
        for x in calendar_list['items']:
            if str(x['summary']) == str(message.guild.name):
                calId = x['id']
                print(calId)

        
        wordList = message.content.split()
        reminderName = wordList[1]
        print(wordList)
        
        events_result = service.events().list(calendarId=calId).execute()
        events = events_result.get('items', [])
        print(events)
        target = "notFound"
        for event in events:
            if event['summary'] == reminderName:
                eventId = event['id']
                print(eventId)
                service.events().delete(calendarId=calId, eventId=eventId).execute()
                await message.channel.send('Reminder Deleted')
                target = "found"

        if target == "notFound":
            await message.channel.send('Reminder Not Found')
        
    #list reminders
    if message.content.startswith('$listreminders'):
        #Message Format: $listreminders
        for x in calendar_list['items']:
            if str(x['summary']) == str(message.guild.name):
                calId = x['id']
                print(calId)
 
        
        events_result = service.events().list(calendarId=calId).execute()
        events = events_result.get('items', [])
        print(events)
        if not events:
            await message.channel.send('No upcoming reminders found.')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            date = start.split("T")
            time = date[1].split("-")
            await message.channel.send(str(date[0]) + " " + str(time[0]) + " " + event['summary'])

    #change reminder
    if message.content.startswith('$changereminder'):
        #Message Format: $changereminder <reminderName> <YYYY-MM-DD> <HH:MM>
        for x in calendar_list['items']:
            if str(x['summary']) == str(message.guild.name):
                calId = x['id']
                print(calId)
        
        wordList = message.content.split()
        reminderName = wordList[1]
        reminderDate = wordList[2]
        reminderTime = wordList[3]
        print(wordList)
        
        events_result = service.events().list(calendarId=calId).execute()
        events = events_result.get('items', [])
        print(events)
        target = "notFound"
        for event in events:
            if event['summary'] == reminderName:
                eventId = event['id']
                print(eventId)
                event = {'summary': reminderName, 
                'start': {'dateTime': reminderDate + "T" + reminderTime + ":00-05:00"},
                'end': {'dateTime': reminderDate + "T" + reminderTime +  ":59-05:00"},
                
                }
                print(event)
                event = service.events().update(calendarId=calId, eventId=eventId, body=event).execute()
                await message.channel.send('Reminder Changed')
                target = "found"

        if target == "notFound":
            await message.channel.send('Reminder Not Found')
        
    


client.run(TOKEN)




