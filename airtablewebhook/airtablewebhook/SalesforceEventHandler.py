from __future__ import absolute_import, unicode_literals
from .models import AirtableEntry, BaseNamesInUsage
from airtable import Airtable
import os
from time import sleep
from numpy import array, delete
from copy import copy
import requests
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from googleapiclient import discovery
from google.auth.transport.requests import Request
from itertools import tee, filterfalse
import pickle

def checkBaseUsage(func):
    """ Decorator that: 
     1) Determines if the request date is properly formatted, if not it fixes the format.
     2) Determines if the Airtable Base is an element of BaseNamesInUsage. If so, releases function.
        If not, determines if it exists in airtable, if not sends an error message,
        if so, created entry in BaseNamesInUsage and releases function.
    """
    def wrapper (request):
        if '/' in request['Date']:
            request['Date'] = "{2}-{0}-{1}".format(*request['Date'].split('/'))
        



        base = BaseNamesInUsage.objects.filter(base_name = request["Base Name"])
        if base.exists():
            if baseExistsInAirtable(base[0].base_id):
                request['Base Name'] = base[0].base_id
            else:
                base[0].delete()
                return False
        else:
            # Retrieves from A Google Sheet the Names and Ids of Routes.
            with open('token.pickle','rb') as token:
                creds=pickle.load(token)
            service=discovery.build('sheets','v4',credentials=creds, cache_discovery = False)
            sheet=service.spreadsheets()
            sheetrange='Sheet1!A2:B'
            sheetSearch=sheet.values().get(spreadsheetId=os.environ["BASE_SHEET_ID"],range=sheetrange).execute()
            spreadsheetBases=sheetSearch.get('values',[])
            try:
                baseId = next(b[1] for b in spreadsheetBases if b[0] == request["Base Name"]) 
                newBase = BaseNamesInUsage(base_name = request["Base Name"], date = request["Date"], base_id = baseId)
                newBase.save()
                request['Base Name'] = newBase.base_id
            except Exception as e:
                sendErrorEmail(error= f"Base {request['Base Name']} not found in the Django"+
                    " Database nor in Airtable Base Sheet google sheet. Please Base Name and Base Id to Google Sheet.")
                return False
            if not baseExistsInAirtable(request["Base Name"]):
                return False
        return func(request)
    return wrapper



def addFutureStopsToDatabase(func):
    """ Decorator that checks that today is the route date. If it is, returns function.
        If it is past today's date, saves in database. If it before today's date, deletes from database.  
    """
    def wrapper (request):
        db_route = list(AirtableEntry.objects.filter(base_name__exact = request["Base Name"], 
                stop_date__exact = datetime.strptime(request["Date"],"%Y-%m-%d").date()))

        # Filters changes on routes before today to be ignored.
        date = datetime.strptime(request["Date"],"%Y-%m-%d").date()
        if date < datetime.now().date():
            sendErrorEmail(error = "It seems you are attempting to update a route whose date has already passed. Was this intentional?")
            return True
        
        airtable_updates =[]
        print( "Initial request is: " + str(request))
        # Generator expression for the case of ROUTE_UPDATEs with no routes.
        new_stops = (stops for stops in request["Route Stops"]) if "Route Stops" in request.keys() else ()

        for stop in new_stops:
            print("For Stop: " + str(stop))

            # Removes Tribeca Beverage Location Stop.
            if "185 Lackawanna Ave" in stop["Address"]:
                continue

            # Adds keys to the stop if necessary and make sure each field complies with the database memory capacity.
            stop["Name"] = stop["Name"][:350] if len(stop["Name"]) >= 350 else stop["Name"]
            stop["Date"] = request["Date"]
            stop["Delivered?"] = stop["Delivered?"] if "Delivered?" in stop.keys() else False
            stop["Address"] = stop["Address"][:500] if len(stop["Address"]) >= 500 else stop["Address"]
            stop["Notes"] = stop["Notes"] if "Notes" in stop.keys() else ''
            stop["Notes"] = stop["Notes"][:500] if len(stop["Notes"]) >= 500 else stop["Notes"]
            stop["Apt. #"] = stop["Apt. #"] if "Apt. #" in stop.keys() else ''
            stop["Apt. #"] = stop["Apt. #"][:200] if len(stop["Apt. #"]) >= 200 else stop["Apt. #"]
            stop["Phone Number"] = stop["Phone Number"][:30] if len(stop["Phone Number"]) >= 30 else stop["Phone Number"]
            stop["Equipment Info"] = stop["Equipment Info"] if "Equipment Info" in stop.keys() else ''
            stop["Equipment Info"] = stop["Equipment Info"][:250] if len(stop["Equipment Info"]) >= 250 else stop["Equipment Info"]
            stop["Attachments"] = stop["Attachments"] if ("Attachments" in stop.keys() and len(stop["Attachments"]) <= 250) else ''
            stop["BPA Free"] = stop["BPA Free"] if "BPA Free" in stop.keys() else 'No'
            stop["Water Type"] = stop["Water Type"] if "Water Type" in stop.keys() else ''
            stop["Water Type"] = stop["Water Type"][:30] if len(stop["Water Type"]) >= 30 else stop["Water Type"]
            


            # Finds a match in route_stop that agree in Salesforce Ids , if none returns None.
            match = next((route_stop for route_stop in db_route if route_stop.stop_salesforce_id == stop["Salesforce Id"]), None)

            if match:
                stop["Django Id"] = match.django_id
                # If the stop has been marked for removal, and the date is today, adds to salesforce_updates.
                if "Method" in stop.keys() and stop["Method"] == "Stop Removed":
                    if datetime.strptime(request["Date"],"%Y-%m-%d").date() == datetime.now().date():
                        airtable_updates.append(stop)

                # If the stop has any changes from its match, remove the match from the db_route
                elif anyUpdates(stop, match):

                    db_route.remove(match)
                    # If the stop is on the current route, add to airtable_updates (where the updating will occur).
                    if date == datetime.now().date():
                        print("Adding stop " + stop["Name"])
                        airtable_updates.append(stop)
                    # otherwise this is a future stop and can just be directly updated in the database.
                    else:
                        updateEntryInDatabaseFromJson(request["Base Name"], stop, method = "Not Inserted")
                else:
                    db_route.remove(match)
            # If there is no match found for the stop        
            else:
                # If the stop is for the future, insert into the Database.
                if date > datetime.now().date():
                    insertEntryInDatabaseFromJson(request["Base Name"], stop, method = "Not Inserted")
                # Otherwise, the stop is for today. Adds to airtable_updates, which is passed to handleRouteUpdate.
                elif date == datetime.now().date():
                    airtable_updates.append(stop)
        # Whatever hasn't been matched, means that it is not on the current version of the route, which means it should be deleted.  
        airtable_updates+=jsonize(db_route, method = "Stop Removed")
        print(str(airtable_updates) + "dfafdsa")
        # creates a new request object that passes on this information.
        if date == datetime.now().date():
            updateDatabase(request["Base Name"],airtable_updates)
            request = {
                "Method"      : "ROUTE_UPDATE",
                "Route Stops" : airtable_updates,
                "Date"        : request["Date"],
                "Base Name"   : request["Base Name"]
            }
            print(request)
            return func(request)
        else:
            return True
    return wrapper



@checkBaseUsage
@addFutureStopsToDatabase
def handleRouteUpdate(request):
    air = Airtable(request["Base Name"],"Table 1", os.environ['AIRTABLE_APIKEY'])
    
    (routeStops := list(AirtableEntry.objects.filter(base_name__exact = request["Base Name"],
                                            stop_date__exact = datetime.now().date()))).sort(key = lambda x: x.stop_number)

    # Retrieves all records from the database associated with the table and
    # the route date.
    for stop in air.get_all():

        match = next((route_stop for route_stop in routeStops if route_stop.stop_salesforce_id == stop["fields"]["Salesforce Id"]), None)
        stop["fields"]["Airtable Id"] = stop["id"]
        stop = stop["fields"]
        if match:
            updateEntryInDatabaseFromMatch(stop,match)

        deleteStopInAirtable(air, stop["Airtable Id"])


    print(routeStops)
    for routeStop in jsonize(routeStops):
        addStopInAirtable(air, routeStop)
    
    return True



        

@checkBaseUsage
def handleRouteDelete(request):
    """ Handler for Salesforce JSON request to delete route in Salesforce,
    returns None.
    
    Argument request of the form:
        request = {
                    "Method" : "ROUTE_DELETE",
                    "Date" : Date,
                    "Base Name" : Base_Name  
                }


    """
    # Retrieves all records associated with the Base for the date.
    routeStops = AirtableEntry.objects.filter(base_name__exact = request["Base Name"],
                                              stop_date__exact = request["Date"])
    # Deletes the records from the Django Database.
    updateDatabase(request["Base Name"], jsonize(routeStops, method = "Stop Removed"))

    # Deletes the records from Airtable.
    if  datetime.strptime(request["Date"],"%Y-%m-%d").date() == datetime.now().date():
        air = Airtable(request["Base Name"],"Table 1", os.environ['AIRTABLE_APIKEY'])
        for stop in air.get_all():
            deleteStopInAirtable(air,stop["id"])
    return True






def updateEntryInDatabaseFromJson(base,updatedStop, method = "Inserted in Table"):
    """ Updates an already existing stop in Django Database """
    djangoEntry = AirtableEntry.objects.get(django_id = updatedStop["Django Id"])
    djangoEntry.base_name                = base
    djangoEntry.stop_name                = updatedStop["Name"]
    djangoEntry.stop_airtable_id         = updatedStop["Airtable Id"] if "Airtable Id" in updatedStop.keys() else ''
    djangoEntry.stop_salesforce_id       = updatedStop["Salesforce Id"]
    djangoEntry.stop_date                = updatedStop["Date"]
    djangoEntry.stop_address             = updatedStop["Address"]
    djangoEntry.stop_delivered           = updatedStop["Delivered?"] if "Delivered?" in updatedStop.keys() else False
    djangoEntry.stop_bottles_dropped_off = updatedStop["Bottles Dropped Off"]
    djangoEntry.stop_bottles_picked_up   = updatedStop["Bottles Picked Up"]
    djangoEntry.stop_number              = updatedStop["Stop Number"]
    djangoEntry.stop_notes               = updatedStop["Notes"] if "Notes" in updatedStop.keys() else ''
    djangoEntry.stop_phone_number        = updatedStop["Phone Number"]
    djangoEntry.stop_apt_number          = updatedStop["Apt. #"] if "Apt. #" in updatedStop.keys() else ''
    djangoEntry.stop_bottles_to_deliver  = updatedStop["Bottles to Deliver"]
    djangoEntry.stop_equipment           = updatedStop["Equipment Info"] if "Equipment Info" in updatedStop.keys() else ''
    djangoEntry.method                   = method
    djangoEntry.stop_attachment          = updatedStop["Attachments"] if "Attachments" in updatedStop.keys() else ''
    djangoEntry.save()
    return None

def updateEntryInDatabaseFromMatch(updatedStop, djangoEntry):
    """ Updates an already existing stop in Django Database """
    djangoEntry.stop_name                = updatedStop["Name"]
    djangoEntry.stop_date                = updatedStop["Date"]
    djangoEntry.stop_address             = updatedStop["Address"]
    djangoEntry.stop_delivered           = updatedStop["Delivered?"] if "Delivered?" in updatedStop.keys() else False
    djangoEntry.stop_bottles_dropped_off = updatedStop["Bottles Dropped Off"]
    djangoEntry.stop_bottles_picked_up   = updatedStop["Bottles Picked Up"]
    djangoEntry.stop_notes               = updatedStop["Notes"] if "Notes" in updatedStop.keys() else ''
    djangoEntry.stop_bottles_to_deliver  = updatedStop["Bottles to Deliver"]
    djangoEntry.stop_equipment           = updatedStop["Equipment Info"] if "Equipment Info" in updatedStop.keys() else ''
    djangoEntry.stop_attachment          = updatedStop["Attachments"] if "Attachments" in updatedStop.keys() else ''
    djangoEntry.save()
    return None


def updateDatabase(base,route, method = "Inserted in Table"):
    """ Updates the database based on a list of dictionaries. Creates a record in the case of no "Django Id",
    Deletes a record in the case of Method = "Stop Removed" and updates records otherwise.
        route =[
            {
                "Name"          : Name,
                "Airtable Id"   : Airtable_Id,
                "Salesforce Id" : Salesforce_Id,
                "Address"       : Address,
                "Dropped Off"   : Dropped_Off,
                "Picked Up"     : Picked_Up,
                "Attachment"    : Attachment,
                "Stop Number"   : Stop_Number,
                "Delivered?"    : Delivered,
                "Method"        : Add_To_Route
            },
        ]
    """
    for stop in route:
        if "Django Id" in stop.keys():
            if stop["Method"] == "Stop Removed":
                deleteEntryInDatabaseFromJson(stop)
            else:
                updateEntryInDatabaseFromJson(base,stop, method)
        else:
            insertEntryInDatabaseFromJson(base, stop, method)
    return None

def insertEntryInDatabaseFromJson(base,newStop, method = "Inserted in Table"):
    """ Inserts new stop into Django Database """
    AirtableEntry(
        base_name                = base,
        stop_name                = newStop["Name"],
        stop_airtable_id         = newStop["Airtable Id"] if "Airtable Id" in newStop.keys() else '',
        stop_salesforce_id       = newStop["Salesforce Id"],
        stop_date                = newStop["Date"],
        stop_address             = newStop["Address"],
        stop_delivered           = newStop["Delivered?"] if "Delivered?" in newStop.keys() else False,
        stop_bottles_dropped_off = newStop["Bottles Dropped Off"] if "Bottles Dropped Off" in newStop.keys() else 0,
        stop_bottles_picked_up   = newStop["Bottles Picked Up"] if "Bottles Picked Up" in newStop.keys() else 0,
        stop_number              = newStop["Stop Number"],
        stop_notes               = newStop["Notes"] if "Notes" in newStop.keys() else '',
        stop_phone_number        = newStop["Phone Number"],
        stop_apt_number          = newStop["Apt. #"] if "Apt. #" in newStop.keys() else '',
        stop_bottles_to_deliver  = newStop["Bottles to Deliver"],
        stop_equipment           = newStop["Equipment Info"] if "Equipment Info" in newStop.keys() else '',
        method                   = method,
        stop_attachment          = newStop["Attachments"] if "Attachments" in newStop.keys() else '',
        stop_bpa_free            = newStop["BPA Free"] if "BPA Free" in newStop.keys() else 'No',
        stop_water_type          = newStop["Water Type"] if "Water Type" in newStop.keys() else 'Alkaline',
    ).save()
    return None


def deleteEntryInDatabaseFromJson(deletedStop):
    """ Deletes an already existing stop from Django Database """
    djangoEntry = AirtableEntry.objects.get(django_id = deletedStop["Django Id"])
    djangoEntry.delete()
    return None



def jsonize(route, method = "Update Stop"):
    return [{"Name"                : stop.stop_name,
             "Django Id"           : stop.django_id,
             "Salesforce Id"       : stop.stop_salesforce_id,
             "Airtable Id"         : stop.stop_airtable_id,
             "Address"             : stop.stop_address,
             "Date"                : str(stop.stop_date),
             "Delivered?"          : stop.stop_delivered,
             "Address"             : stop.stop_address,
             "Bottles Picked Up"   : stop.stop_bottles_picked_up,
             "Bottles Dropped Off" : stop.stop_bottles_dropped_off,
             "Stop Number"         : stop.stop_number,
             "Method"              : method,
             "Notes"               : stop.stop_notes,
             "Phone Number"        : stop.stop_phone_number,
             "Apt. #"              : stop.stop_apt_number,
             "Bottles to Deliver"  : stop.stop_bottles_to_deliver,
             "Equipment Info"      : stop.stop_equipment,
             "Base Name"           : stop.base_name,
             "Attachments"         : stop.stop_attachment,
             "BPA Free"            : stop.stop_bpa_free,
             "Water Type"          : stop.stop_water_type,
             } for stop in route]


def anyDuplicates(thelist):
    seen = set()
    for x in thelist:
        if x in seen: return True
        seen.add(x)
    return False

def sendErrorEmail(error):
    message = Mail(
            from_email   = 'info@tribecabeverage.com',
            to_emails    = 'info@tribecabeverage.com',
            subject      = 'Airtable Webhook Error',
            html_content =  error
        )
    sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    response = sg.send(message)
    return None

def sleep_decorator(func):
    def wrapper (*args,**kwargs):
        sleep(1)
        return func(*args,**kwargs)
    return wrapper


def baseExistsInAirtable(base):
    header = {"Authorization" : f"Bearer {os.environ['AIRTABLE_APIKEY']}"}
    r=requests.get(url =f"https://api.airtable.com/v0/{base}/table%201", headers=header )
    if "error" in (response:=r.json()).keys():
        if isinstance(response["error"], dict):
            if response['error']['type']  == "BASE_NOT_FOUND":
                sendErrorEmail(error = f"Base does not exist in Airtable: {base}")
            else:
                sendErrorEmail(error = "Unidentified error in Airtable request in function "+
                f"'airtablewebhook.SalesforceEventHander.checkBaseUsage' with message: {response['error']['message']}")
        elif isinstance(response["error"], str) and response["error"] == "NOT_FOUND":
            sendErrorEmail(error = "Base not found in Airtable request in function "+
                f"'airtablewebhook.SalesforceEventHander.checkBaseUsage' with message: {str(response)}")
        else:
            sendErrorEmail(error = "Unidentified error in Airtable request in function "+
                f"'airtablewebhook.SalesforceEventHander.checkBaseUsage' with message: {str(response)}"
                +"\nMake sure to update google sheet as well!")
        return False
    return response




@sleep_decorator
def replaceStopInAirtable(air,stopId,updatedStop):
    response = air.replace(stopId, standardKwargs(updatedStop))  
    return stopId


@sleep_decorator
def addStopInAirtable(air,stop):
    response = air.insert(standardKwargs(stop))
    return response["id"]

def standardKwargs(json):
    return {"Name"                : json["Name"],
            "Salesforce Id"       : json["Salesforce Id"],
            "Date"                : json["Date"],
            "Notes"               : json["Notes"],
            "Delivered?"          : json["Delivered?"],
            "Address"             : json["Address"],
            "Bottles Picked Up"   : json["Bottles Picked Up"],
            "Bottles Dropped Off" : json["Bottles Dropped Off"],
            "Stop Number"         : json["Stop Number"],
            "Phone Number"        : str(json["Phone Number"]),
            "Apt. #"              : json["Apt. #"],
            "Bottles to Deliver"  : json["Bottles to Deliver"],
            "Equipment Info"      : json["Equipment Info"],
            "BPA Free"            : json["BPA Free"],
            "Water Type"          : json["Water Type"]
            }

@sleep_decorator
def deleteStopInAirtable(air,stopId):
    air.delete(stopId)



def anyUpdates(airtableEntry,djangoEntry):
    return not all([  
        djangoEntry.stop_name                == airtableEntry["Name"],
        djangoEntry.stop_date                == datetime.strptime(airtableEntry["Date"],"%Y-%m-%d").date(),
        djangoEntry.stop_address             == airtableEntry["Address"],
        djangoEntry.stop_delivered           == airtableEntry["Delivered?"],
        djangoEntry.stop_bottles_dropped_off == airtableEntry["Bottles Dropped Off"],
        djangoEntry.stop_bottles_picked_up   == airtableEntry["Bottles Picked Up"],
        djangoEntry.stop_number              == airtableEntry["Stop Number"],
        djangoEntry.stop_notes               == airtableEntry["Notes"],
        djangoEntry.stop_phone_number        == airtableEntry["Phone Number"],
        djangoEntry.stop_apt_number          == airtableEntry["Apt. #"],
        djangoEntry.stop_bottles_to_deliver  == airtableEntry["Bottles to Deliver"],  
        djangoEntry.stop_equipment           == airtableEntry["Equipment Info"],
        djangoEntry.stop_attachment          == airtableEntry["Attachments"],      
    ])

def partition(pred, iterable):
    'Use a predicate to partition entries into false entries and true entries'
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = tee(iterable)
    return list(filter(pred, t2)), list(filterfalse(pred, t1))




def repollRouteInSalesforce():
    print("Repolling Route in Salesforce")





