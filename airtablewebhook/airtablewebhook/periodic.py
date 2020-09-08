import os
import django
import pathlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangowebsite.settings')
from copy import copy, deepcopy
from airtable import Airtable
from .models import BaseNamesInUsage, AirtableEntry
from .tasks import updateRoute
from itertools import tee, filterfalse
import requests
from .SalesforceEventHandler import (
    deleteStopInAirtable, baseExistsInAirtable, updateEntryInDatabaseFromJson,
    repollRouteInSalesforce, jsonize, anyUpdates, partition, anyDuplicates
)
from json import dumps
from datetime import datetime,timedelta
from simple_salesforce import Salesforce
from googleapiclient import discovery
from google.auth.transport.requests import Request
import pickle
from statistics import stdev
from itertools import takewhile






def pollAirtableForUpdates():
    availableBases = [e for e in BaseNamesInUsage.objects.all()]
    # get entries from Airtable
    for availableBase in availableBases:
        if (datetime.now().date() - availableBase.date) > timedelta(days = 30):
            availableBase.delete()
            availableBases.remove(availableBase)

    bases = [[pollBaseForUpdates(base.base_id,base.base_name),base.base_name] for base in availableBases]

    # update Salesforce
    url = 'https://tribecabeverage.salesforce.com/airtablewebhook/'
    myobj = [
        {
            "base_name" : base_name,
            "stops"     : putInSalesforceStyleJSON(base_data)
        }
        for base_data, base_name in bases
    ]
    post = {
        "method" : "ROUTE_UPDATE",
        "data"   :  myobj,
        "updateDate"   : str(datetime.now().date())
    }
    print("post is: " + str(post))
    sf = Salesforce(username = os.environ["SALESFORCE_OAUTH_USERNAME"], password = os.environ["SALESFORCE_OAUTH_PASSWORD"], security_token = os.environ['SALESFORCE_SECURITY_TOKEN'])
    sf.apexecute("airtablewebhook", method = "POST", data = post)
    return post

def putInSalesforceStyleJSON (base_data):
    for stop in base_data:
        stop["salesforceId"]      = stop.pop("Salesforce Id","")
        stop["address"]           = stop.pop("Address","")
        stop["bottlesDroppedOff"] = stop.pop("Bottles Dropped Off",0)
        stop["bottlesPickedUp"]   = stop.pop("Bottles Picked Up", 0)
        stop["stopNumber"]        = stop.pop("Stop Number",0)
        stop["description"]       = stop.pop("Notes","")
        stop["method"]            = stop.pop("Method","Stop Updated")
        stop["phoneNumber"]       = stop.pop("Phone Number","")
        stop["bottlesToDeliver"]  = stop.pop("Bottles to Deliver",0)
        stop["stopDate"]          = stop.pop("Date",str(datetime.now().date()))
        stop["aptNumber"]         = stop.pop("Apt. #", "")
        stop["equipmentInfo"]     = stop.pop("Equipment Info","")
        stop["delivered"]         = stop.pop("Delivered?",False)
        stop["stopName"]          = stop.pop("Name","")
        stop["attachmentUrl"]     = stop.pop("Attachments","")
        stop["bpaFree"]           = stop.pop("BPA Free", "No")
        stop["waterType"]         = stop.pop("Water Type", "Alkaline")
        del stop["Django Id"]
        
    return base_data

def correctRank(airtableData):
    # process airtableData if the stops are not in counting order, by finding correct ordering, and updating the order in Airtable.
    if (rank:=isNotFullRank(airtableData)):
        airtableData = rank
    return airtableData        

def pollBaseForUpdates(base_id, base_name):
    """
        Returns records to be updated in Salesforce.
    """

    oldDjangoData = AirtableEntry.objects.filter(base_name__exact = base_id, stop_date__lte = (datetime.now().date() - timedelta(days = 2)))
    for oldDjangoEntry in oldDjangoData:
        oldDjangoEntry.delete()

    # Tests if Airtable base exists, and grabs data.
    airtableData = x["records"] if (x:=baseExistsInAirtable(base_id)) else []

    # Reformats to Jsonized form.
    for airtableEntry in airtableData:
        airtableEntry["fields"]["Airtable Id"] = airtableEntry["id"] 

    # Filters out entries whose date is not today.
    airtableData = [airtableEntry["fields"] for airtableEntry in airtableData if datetime.strptime(airtableEntry["fields"]["Date"],"%Y-%m-%d").date() == datetime.now().date()]
    # Filters out entries with no Salesforce Id.
    airtableData = list(filter(lambda x: "Salesforce Id" in x.keys(),airtableData)) 

    # Gets all Django Database Entries for the base_name and today
    djangoData = list(AirtableEntry.objects.filter(base_name__exact = base_id, stop_date__exact = datetime.now().date()))

    salesforce_updates, database_fixes = [], []

    # For each entry, looks for a match in the Database.
    for airtableEntry in airtableData:
        print(str(airtableEntry))
        match = next((route_stop for route_stop in djangoData if route_stop.stop_salesforce_id == airtableEntry["Salesforce Id"]), None)

        if match:

            airtableEntry["Delivered?"] = airtableEntry["Delivered?"] if "Delivered?" in airtableEntry.keys() else False
            airtableEntry["Apt. #"] = airtableEntry["Apt. #"] if "Apt. #" in airtableEntry.keys() else ''
            airtableEntry["Equipment Info"] = airtableEntry["Equipment Info"] if "Equipment Info" in airtableEntry.keys() else ''
            airtableEntry["Method"] = airtableEntry["Method"] if "Method" in airtableEntry.keys() else "Stop Updated"
            airtableEntry["Phone Number"] = airtableEntry["Phone Number"] if "Phone Number" in airtableEntry.keys() else ''
            airtableEntry["Bottles to Deliver"] = airtableEntry["Bottles to Deliver"] if "Bottles to Deliver" in airtableEntry.keys() else 0
            airtableEntry["Bottles Dropped Off"] = airtableEntry["Bottles Dropped Off"] if "Bottles Dropped Off" in airtableEntry.keys() else 0
            airtableEntry["Bottles Picked Up"] = airtableEntry["Bottles Picked Up"] if "Bottles Picked Up" in airtableEntry.keys() else 0
            airtableEntry["Notes"] = airtableEntry["Notes"] if "Notes" in airtableEntry.keys() else ""
            airtableEntry["Stop Number"] = airtableEntry["Stop Number"] if "Stop Number" in airtableEntry.keys() else 0
            airtableEntry["Name"] = airtableEntry["Name"] if "Name" in airtableEntry.keys() else ""
            airtableEntry["Address"] = airtableEntry["Address"] if "Address" in airtableEntry.keys() else ""
            airtableEntry["Date"] = airtableEntry["Date"] if "Date" in airtableEntry.keys() else str(datetime.now().date())
            airtableEntry["Attachments"] = airtableEntry["Attachments"][0]["url"] if "Attachments" in airtableEntry.keys() else ""
            airtableEntry["BPA Free"] = airtableEntry["BPA Free"] if "BPA Free" in airtableEntry.keys() else "No"
            airtableEntry["Water Type"] = airtableEntry["Water Type"] if "Water Type" in airtableEntry.keys() else "Alkaline"
            airtableEntry["Django Id"] = match.django_id 

            if anyUpdates(airtableEntry, match):
                print('Update Found!!')
                UpdateAttachment = True

                if match.stop_attachment != '':
                    UpdateAttachment = False

                updateEntryInDatabaseFromJson(base_id,airtableEntry, method = "Inserted in Table")
                djangoData.remove(match)

                if not UpdateAttachment:
                    airtableEntry["Attachments"] = ""
                salesforce_updates.append(airtableEntry)
            else:
                djangoData.remove(match)

        
    noninsertedDjangoData, insertedDjangoData = partition(lambda x: x.method == "Not Inserted", djangoData)

    for djangoEntry in insertedDjangoData:
        djangoEntry.delete()
        print("Deleting djangoEntry: " + str(djangoEntry))
    
    if (x:=jsonize(noninsertedDjangoData)):
        airtableData+=x

    print(airtableData)
    if duplicateStops(airtableData):
        airtableData = repollRouteInSalesforce()

    if airtableData and (noninsertedDjangoData or (airtableData:= isNotFullRank(airtableData))):
        
        req = {
            "Method"      : "ROUTE_UPDATE",
            "Date"        : str(datetime.now().date()),
            "Base Name"   : base_name,
            "Route Stops" : airtableData
        }
        print(req)
        updateRoute.delay(req)
    return salesforce_updates
    


def isNotFullRank(airtableStops):
    stops = copy(airtableStops)
    maxstop = max(stops,key = lambda x: x["Stop Number"])
    corrected_list = []
    def count():
        for x in range(1,len(stops)+1):
            yield x
    inOrder = []
    l = count()       
    while stops:
        print("Might be Stuck")
        counter = next(l,None)
        if counter:
            count_matching = False
            correction = -1
            while not count_matching:
                correction += 1
                for i in range(len(stops)):
                    if stops[i]["Stop Number"] == counter+correction:
                        for stop in stops:
                            stop["Stop Number"] -= correction
                        corrected_list.append(stops.pop(i))
                        count_matching = True
                        inOrder.append(correction == 0)
                        break
        else:
            break
    if not all(inOrder):
        return corrected_list
    else:
        return False

def duplicateStops(airtableData):
    stops = [airtableEntry["Stop Number"] for airtableEntry in airtableData if airtableEntry]
    ids = [airtableEntry["Salesforce Id"] for airtableEntry in airtableData if airtableEntry]
    return anyDuplicates(stops) or anyDuplicates(ids)        








def updateDailyReport():
    availableBases = [e for e in BaseNamesInUsage.objects.all()]
    availableBases.sort(key = lambda x: x.base_name)
    spreadsheetId = os.environ['DRIVING_REPORT_SPREADSHEET_ID']


    with open('token.pickle','rb') as token:
        creds = pickle.load(token)
    service = discovery.build('sheets','v4',credentials=creds)
    sheet = service.spreadsheets()

    summaryTable = sheet.values().get(spreadsheetId = spreadsheetId,
                                            range = f"Summary!A3:{column_string(len(availableBases)+2)}").execute().get("values",[])
    updateBody = deepcopy(summaryTable[:10])
    updateBody[0][0]= str(datetime.now().date())

    print(str(summaryTable))

    table = [[*x,i] for i,x in enumerate(summaryTable)]
    tenthElement = list(filter(lambda x: x[-1]%10==0,table))
    dateTable = list(takewhile(lambda x:(datetime.now()-datetime.strptime(x[0], '%m/%d/%Y'))<=timedelta(days=31) if x[0] else True, tenthElement))
    print(dateTable)
    dateTable = list(takewhile(lambda x: int(x[-1]) < int(dateTable[-1][-1]),table))
    dateTable = [[x[:-1]] for x in dateTable]

    updateBody += dateTable

    request = sheet.values().batchUpdate(
        spreadsheetId = spreadsheetId,
        body = {
            "valueInputOption" :"USER_ENTERED",
            "data" : [
                {
                    "values": [[availableBase.base_name for availableBase in availableBases]],
                    "range" : f"Summary!C2:{column_string(len(availableBases)+2)}2"
                },
                {
                    "values": updateBody,
                    "range": f"Summary!A3:{column_string(len(availableBases)+2)}{len(updateBody)+2}"
                }
            ]
        }
    ).execute()
    request =sheet.values().update(spreadsheetId = spreadsheetId,
            range = f"Summary!A3:{column_string(len(availableBases)+2)}{len(updateBody)+2}",
            valueInputOption = 'USER_ENTERED',
            body = {
                'range':f"Summary!A3:{column_string(len(availableBases)+2)}{len(updateBody)+2}",
                'values': updateBody
            }
        ).execute()                                            

    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheetId).execute()
    sheetsInGSpread =[x["properties"]["title"] for x in sheet_metadata.get('sheets', '')]


    for availableBase in availableBases:
        if availableBase.base_name not in sheetsInGSpread: 
            sheet.batchUpdate(
                spreadsheetId = spreadsheetId,
                body = {
                    "requests" : [
                        {
                            "addSheet": {
                                "properties" : {"title": f"{availableBase.base_name}"}
                            }
                        }
                    ]
                }
            ).execute()  
            sheet.values().batchUpdate(
                spreadsheetId = spreadsheetId,
                body = {
                    "valueInputOption" :"USER_ENTERED",
                    "data" : [
                        {
                            "values": [["Name",
                                        "Address",
                                        "Delivered?",
                                        "Bottles Dropped Off",	
                                        "Bottles Picked Up",
                                        "Notes",
                                        "Date",
                                        "Stop Number",
                                        "Phone Number",
                                        "Apt. #",
                                        "Bottles to Deliver",
                                        "Equipment Info",
                                        "BPA Free",
                                        "Water Type"]],
                            "range" : f"{availableBase.base_name}!A1:{column_string(14)}1"
                        },
                        {
                            "values": updateBody,
                            "range": f"Summary!A3:{column_string(len(availableBases)+2)}{len(updateBody)+2}"
                        }
                    ]
                }
            ).execute()
        
        # Go through airtable data and add each entry to the top.
        # pushing down the older data
        # delete data older than 30 days.



        if (airtableData:=baseExistsInAirtable(availableBase.base_id)):
            airtableData = airtableData["records"]
            airtableData = [airtableEntry["fields"] for airtableEntry in airtableData]
            print(airtableData)
            airtableData = list(filter(lambda x: datetime.strptime(x["Date"],"%Y-%m-%d").date() == (datetime.now()-timedelta(days=1)).date(), airtableData))
            print(airtableData)
            for airtableEntry in airtableData:
                airtableEntry["Delivered?"] = airtableEntry["Delivered?"] if "Delivered?" in airtableEntry.keys() else False
                airtableEntry["Apt. #"] = airtableEntry["Apt. #"] if "Apt. #" in airtableEntry.keys() else ''
                airtableEntry["Equipment Info"] = airtableEntry["Equipment Info"] if "Equipment Info" in airtableEntry.keys() else ''
                airtableEntry["Method"] = airtableEntry["Method"] if "Method" in airtableEntry.keys() else "Stop Updated"
                airtableEntry["Phone Number"] = airtableEntry["Phone Number"] if "Phone Number" in airtableEntry.keys() else ''
                airtableEntry["Bottles to Deliver"] = airtableEntry["Bottles to Deliver"] if "Bottles to Deliver" in airtableEntry.keys() else 0
                airtableEntry["Bottles Dropped Off"] = airtableEntry["Bottles Dropped Off"] if "Bottles Dropped Off" in airtableEntry.keys() else 0
                airtableEntry["Bottles Picked Up"] = airtableEntry["Bottles Picked Up"] if "Bottles Picked Up" in airtableEntry.keys() else 0
                airtableEntry["Notes"] = airtableEntry["Notes"] if "Notes" in airtableEntry.keys() else ""
                airtableEntry["Stop Number"] = airtableEntry["Stop Number"] if "Stop Number" in airtableEntry.keys() else 0
                airtableEntry["Name"] = airtableEntry["Name"] if "Name" in airtableEntry.keys() else ""
                airtableEntry["Address"] = airtableEntry["Address"] if "Address" in airtableEntry.keys() else ""
                airtableEntry["Date"] = airtableEntry["Date"] if "Date" in airtableEntry.keys() else str(datetime.now().date())
                airtableEntry["Attachments"] = airtableEntry["Attachments"][0]["url"] if "Attachments" in airtableEntry.keys() else ""
                airtableEntry["BPA Free"] = airtableEntry["BPA Free"] if "BPA Free" in airtableEntry.keys() else "No"
                airtableEntry["Water Type"] = airtableEntry["Water Type"] if "Water Type" in airtableEntry.keys() else "Alkaline"

            tableEntries = sheet.values().get(spreadsheetId = spreadsheetId,
                                            range = f"{availableBase.base_name}!A2:N").execute().get("values",[])


            stops_with_attachments = sum([1 if x["Attachments"] else 0 for x in airtableData])
            
            dateTable = list(takewhile(lambda x:(datetime.now().date()-datetime.strptime(x[6], '%Y-%m-%d'))<=timedelta(days=31) if x[6] else True, tableEntries))

            updateEntries = [[x["Name"],x["Address"],x["Delivered?"],
                              x["Bottles Dropped Off"], x["Bottles Picked Up"],
                              x["Notes"],x["Date"],x["Stop Number"],
                              x["Phone Number"],x["Apt. #"],
                              x["Bottles to Deliver"], x["Equipment Info"],
                              x["BPA Free"],x["Water Type"]] for x in airtableData]
            print(updateEntries)
            if updateEntries:
                bottles_delivered = sum([int(x[3]) for x in updateEntries])
                bottles_picked_up  = sum([int(x[4]) for x in updateEntries])
                stops_delivered = sum([1 if x[2] else 0 for x in updateEntries])
                total_number_of_stops = len(updateEntries)
                percent_delivered = stops_delivered/total_number_of_stops
                should_be_delivered = sum([int(x[10]) for x in updateEntries])
                should_be_picked_up = sum([1 if x[4]>0 else 0 for x in updateEntries if x[2]])
                percent_with_attachments = stops_with_attachments/total_number_of_stops
                drop_off_completion = bottles_delivered/should_be_delivered
                if stops_delivered:
                    percent_picked_up = should_be_picked_up/stops_delivered
                    pick_up_completion = should_be_picked_up/stops_delivered
                else:
                    percent_picked_up = "N/A"
                    pick_up_completion = "N/A"

            else:
                bottles_delivered = 0
                bottles_picked_up  = 0
                stops_delivered = 0
                total_number_of_stops = 0
                percent_delivered = "N/A"
                pick_up_completion = "N/A"
                percent_picked_up = "N/A"
                drop_off_completion = "N/A"
                percent_with_attachments = "N/A"                
            
            updateEntries+=dateTable

            if updateEntries:
                average_route_completion = sum([1 if x[2] else 0 for x in updateEntries])/len(updateEntries)
                average_route_consistency = stdev([1 if x[2] else 0 for x in updateEntries])
            else:
                average_route_completion = "N/A"
                average_route_consistency = "N/A"
    

            sheet.values().batchUpdate(
                spreadsheetId = spreadsheetId,
                body = {
                    "valueInputOption" :"USER_ENTERED",
                    "data" : [
                        {
                            "values": updateEntries,
                            "range" : f"{availableBase.base_name}!A2:N{2+len(updateEntries)}"
                        },
                        {
                            "values": [[bottles_delivered],
                                       [bottles_picked_up],
                                       [stops_delivered],
                                       [total_number_of_stops],
                                       [percent_delivered],
                                       [drop_off_completion],
                                       [pick_up_completion],
                                       [average_route_completion],
                                       [average_route_consistency],
                                       [percent_with_attachments]],
                            "range": f"Summary!{column_string(int(availableBase.base_name)+2)}3:{column_string(int(availableBase.base_name)+2)}12"
                        }
                    ]
                }
            ).execute()






def column_string(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string