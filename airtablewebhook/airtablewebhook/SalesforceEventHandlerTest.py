from SalesforceEventHandler import meshStops
import requests
import json
import os
from requests.auth import HTTPBasicAuth


def validateMeshStops():
currentStops =[
            {
                "Name"          : "Rene Descartes",
                "Salesforce Id" : "3adffwfdsafd",
                "Address"       : "Paris",
                "Bottles Dropped Off"   : 3,
                "Bottles Picked Up"     : 2,
                "Attachment"    : None,
                "Stop Number"   : 1,
                "Delivered?"     : False,
                "Notes"         : "Famous French mathematician, philosopher, and scientist.",
                "Method"        : "Update Stop"
            },
            {
                "Name"          : "Hugo De Vries",
                "Salesforce Id" : "fae13242sfas",
                "Address"       : "Netherlands",
                "Bottles Dropped Off"   : 6,
                "Bottles Picked Up"     : 3,
                "Attachment"    : None,
                "Notes"         : "Dutch botanist and one of the first geneticists. He is known chiefly for suggesting the concept of genes.",
                "Stop Number"   : 2,
                "Delivered?"     : False,
                "Method"        : "Update Stop"
            },
            {
                "Name"          : "Club des Jacobins",
                "Salesforce Id" : "fs12351jaf",
                "Address"       : "France",
                "Bottles Dropped Off"   : 1,
                "Bottles Picked Up"     : 63,
                "Attachment"    : None,
                "Stop Number"   : 3,
                "Notes"         : "The most influential political club during the French Revolution of 1789. The period of its political ascendancy includes the Reign of Terror.",
                "Delivered?"     : False,
                "Method"        : "Update Stop"
            },
            {
                "Name"          : "Jose Luis Rodriguez Zapatero",
                "Salesforce Id" : "rwa321fdsa",
                "Address"       : "Spain",
                "Bottles Dropped Off"   : 74,
                "Bottles Picked Up"     : 21,
                "Attachment"    : None,
                "Stop Number"   : 4,
                "Notes"         : "A Spanish politician and member of the Spanish Socialist Workers' Party (PSOE). He was the Prime Minister of Spain being elected for two terms.",
                "Delivered?"     : False,
                "Method"        : "Update Stop"
            },
]
newStops =[
            {
                "Name"                  : "Francois Andrieux",
                "Salesforce Id"         : "efsafdsafds",
                "Address"               : "Strasbourg",
                "Bottles Dropped Off"   : 0,
                "Bottles Picked Up"     : 2,
                "Attachment"            : None,
                "Stop Number"           : 2,
                "Notes"                 : "A French man of letters and playwright.",
                "Delivered?"            : False,
                "Method"                : "Add Stop"
            },
            {
                "Name"                  : "Jose Luis Rodriguez Zapatero",
                "Salesforce Id"         : "rwafdsa",
                "Address"               : "Spain",
                "Bottles Dropped Off"   : 74,
                "Bottles Picked Up"     : 21,
                "Attachment"            : None,
                "Stop Number"           : 4,
                "Notes"                 : "A Spanish politician and member of the Spanish Socialist Workers' Party (PSOE). He was the Prime Minister of Spain being elected for two terms.",
                "Delivered?"            : False,
                "Method"                : "Stop Removed"
            },
            {
                "Name"                  : "Arthur Mortiz Schoenflies",
                "Salesforce Id"         : "efsfasdv",
                "Address"               : "Germany",
                "Bottles Dropped Off"   : None,
                "Bottles Picked Up"     : None,
                "Attachment"            : None,
                "Notes"                 : "A German mathematician, known for his contributions to the application of group theory to crystallography, and for work in topology.",
                "Stop Number"           : 1,
                "Delivered"             : False,
                "Method"                : "Add Stop"
            },
            {
                "Name"          : "Club des Jacobins",
                "Salesforce Id" : "fs12351jaf",
                "Address"       : "France",
                "Bottles Dropped Off"   : 1,
                "Bottles Picked Up"     : 63,
                "Attachment"    : None,
                "Stop Number"   : 3,
                "Notes"         : "The most influential political club during the French Revolution of 1789. The period of its political ascendancy includes the Reign of Terror.",
                "Delivered?"     : False,
                "Method"        : "Update Stop"
            },

]
    meshedStops = meshStops(currentStops,newStops)
    shouldBe = (
        [
            {
                'Name': 'Arthur Mortiz Schoenflies',
                'Salesforce Id': 'efsfasdv',
                'Address': 'Germany',
                'Dropped Off': None,
                'Picked Up': None,
                'Attachment': None,
                'Stop Number': 1,
                'Delivered': False,
                'Method': 'Add Stop'
            },
            {
                'Name': 'Francois Andrieux',
                'Salesforce Id': 'efsafdsafds',
                'Address': 'Strasbourg',
                'Dropped Off': 0,
                'Picked Up': 2,
                'Attachment': None,
                'Stop Number': 2,
                'Delivered': False,
                'Method': 'Add Stop'
            },
            {
                'Name': 'Rene Descartes',
                'Airtable Id': 1,
                'Salesforce Id': '3fwfdsafd',
                'Address': 'Paris',
                'Dropped Off': 3,
                'Picked Up': 2,
                'Attachment': None,
                'Stop Number': 3,
                'Delivered': False,
                'Method': 'Update Stop'
            },
            {
                'Name': 'Hugo De Vries',
                'Airtable Id': 2,
                'Salesforce Id': 'faesfas',
                'Address': 'Netherlands',
                'Dropped Off': 6,
                'Picked Up': 3,
                'Attachment': None,
                'Stop Number': 4,
                'Delivered': False,
                'Method': 'Update Stop'
            },
            {
                'Name': 'Club des Jacobins',
                'Airtable Id': 3,
                'Salesforce Id': 'fsjaf',
                'Address': 'France',
                'Dropped Off': 1,
                'Picked Up': 63,
                'Attachment': None,
                'Stop Number': 5,
                'Delivered': False,
                'Method': 'Update Stop'
            }
        ],
        [
            {
                'Name': 'Jose Luis Rodriguez Zapatero',
                'Airtable Id': 4,
                'Salesforce Id': 'rwafdsa',
                'Address': 'Spain',
                'Dropped Off': 74,
                'Picked Up': 21,
                'Attachment': None,
                'Stop Number': 4,
                'Delivered': False,
                'Method': 'Update Stop'
            }
        ]
    )
    assert meshStops == shouldBe
    return True

def validateHandleRouteCreateFromView():

    url = 'http://127.0.0.1:8000/airtablewebhook/'
    myobj = {
                "Method" : "ROUTE_CREATED",
                "Route Stops" : [
                        {
                            "Name"          : "Sun-tzu Suan-ching",
                            "Salesforce Id" : "fdalfdsasfd",
                            "Address"       : "Sixteen Kingdoms",
                            "Bottles Dropped Off"   : 6,
                            "Bottles Picked Up"     : 0,
                            "Attachment"    : None,
                            "Stop Number"   : 1,
                            "Delivered?"    : False,
                            "Notes"         : "Famous mathematician who discovered the Chinese Remainder Theorem and formulated an early solution to some Diophantine Equations",
                            "Method"        : "Stop Added"
                        }
                    ],
                "Date" : "2020-5-2",
                "Table Name" : "Table 4"  
            }

    x = requests.post(url, data = json.dumps(myobj))

    assert x.text == "Success"
    return True

def validateHandleRouteDeleteFromView():
    url = 'http://127.0.0.1:8000/airtablewebhook/'
    myobj = {
            "Method" : "ROUTE_CREATED",
            "Route Stops" : [
                        {
                            "Name"                  : "Vasco da Gama",
                            "Salesforce Id"         : "esfasdsa",
                            "Address"               : "Sines, Alentejo, Kingdom of Portugal",
                            "Bottles Dropped Off"   : 2,
                            "Bottles Picked Up"     : 7,
                            "Stop Number"           : 1,
                            "Delivered?"            : False,
                            "Notes"                 : "Portuguese exploreer and the first European to reach India by sea in 1497",
                            "Date"                  : "2020-4-2"
                        }
                ],
            "Date" : "2020-5-2",
            "Table Name" : "Table 4"  
        }
    x = requests.post(url, data = json.dumps( myobj ))

url = 'http://127.0.0.1:8000/airtablewebhook/'
myobj = {
            "Method" : "ROUTE_DELETED",
            "Date" : "2020-5-2",
            "Base Name" : "Deliveries"  
        }

x = requests.post(url, data = json.dumps(myobj),auth = HTTPBasicAuth(os.environ["SALESFORCE_USERNAME"],os.environ["SALESFORCE_PASSWORD"]))

    assert x.text == "Success"
    return True

def validateHandleRouteUpdateFromView():

url = 'http://airtable-webhook.herokuapp.com/airtablewebhook/'
myobj = {
            "Method" : "ROUTE_UPDATED",
            "Route Stops" : [
                    {
                        "Name"                  : "Rene Descartes",
                        "Salesforce Id"         : "31235fwasafd",
                        "Address"               : "Paris",
                        "Bottles Dropped Off"   : 3,
                        "Bottles Picked Up"     : 2,
                        "Attachment"            : None,
                        "Stop Number"           : 1,
                        "Delivered?"            : False,
                        "Notes"                 : "Famous French mathematician, philosopher, and scientist.",
                        "Method"                : "Update Stop",
                        "Phone Number"          : '9734032111',
                        "Bottles to Deliver"    : 3
                    },
                    {
                        "Name"                  : "Hugo De Vries",
                        "Salesforce Id"         : "ffas3251das",
                        "Address"               : "Netherlands",
                        "Bottles Dropped Off"   : 6,
                        "Bottles Picked Up"     : 3,
                        "Attachment"            : None,
                        "Notes"                 : "Dutch botanist and one of the first geneticists. He is known chiefly for suggesting the concept of genes.",
                        "Stop Number"           : 2,
                        "Delivered?"            : False,
                        "Method"                : "Update Stop",
                        "Phone Number"          : '9734032111',
                        "Bottles to Deliver"    : 3
                    },
                    {
                        "Name"                  : "Club des Jacobins",
                        "Salesforce Id"         : "fasd1325fs",
                        "Address"               : "France",
                        "Bottles Dropped Off"   : 1,
                        "Bottles Picked Up"     : 63,
                        "Attachment"            : None,
                        "Stop Number"           : 3,
                        "Notes"                 : "The most influential political club during the French Revolution of 1789. The period of its political ascendancy includes the Reign of Terror.",
                        "Delivered?"            : False,
                        "Method"                : "Update Stop",
                        "Phone Number"          : '9734032111',
                        "Bottles to Deliver"    : 3
                    },
                    {
                        "Name"                  : "Jose Luis Rodriguez Zapatero",
                        "Salesforce Id"         : "rwf1351da",
                        "Address"               : "Spain",
                        "Bottles Dropped Off"   : 74,
                        "Bottles Picked Up"     : 21,
                        "Attachment"            : None,
                        "Stop Number"           : 4,
                        "Notes"                 : "A Spanish politician and member of the Spanish Socialist Workers' Party (PSOE). He was the Prime Minister of Spain being elected for two terms.",
                        "Delivered?"            : False,
                        "Method"                : "Update Stop",
                        "Phone Number"          : '9734032111',
                        "Bottles to Deliver"    : 3
                    },
                ],
            "Date" : "2020-9-3",
            "Base Name" : "Deliveries"  
        }
x = requests.post(url, data = json.dumps(myobj),auth = HTTPBasicAuth(os.environ["SALESFORCE_USERNAME"],os.environ["SALESFORCE_PASSWORD"]))


url = 'http://airtable-webhook.herokuapp.com/airtablewebhook/'
myobj = {
        "Method" : "ROUTE_UPDATED",
        "Route Stops" : [

                {
                    "Name"                  : "Francois Andrieux",
                    "Salesforce Id"         : "efsafdsafds",
                    "Address"               : "Strasbourg",
                    "Bottles Dropped Off"   : 0,
                    "Bottles Picked Up"     : 2,
                    "Attachment"            : None,
                    "Stop Number"           : 1,
                    "Notes"                 : "A French man of letters and playwright.",
                    "Delivered?"            : False,
                    "Method"                : "Add Stop",
                    "Phone Number"          : '9734032111',
                    "Bottles to Deliver"    : 3
                },
                {
                    "Name"                  : "Arthur Mortiz Schoenflies",
                    "Salesforce Id"         : "efsfasdv",
                    "Address"               : "Germany",
                    "Bottles Dropped Off"   : 0,
                    "Bottles Picked Up"     : 0,
                    "Attachment"            : None,
                    "Notes"                 : "A German mathematician, known for his contributions to the application of group theory to crystallography, and for work in topology.",
                    "Stop Number"           : 2,
                    "Delivered?"            : False,
                    "Method"                : "Add Stop",
                    "Phone Number"          : '9734032111',
                    "Bottles to Deliver"    : 3
                },
                {
                    "Name"          : "Club des Jacobins",
                    "Salesforce Id" : "fasd1325fs",
                    "Address"       : "France",
                    "Bottles Dropped Off"   : 1,
                    "Bottles Picked Up"     : 63,
                    "Attachment"    : None,
                    "Stop Number"   : 3,
                    "Notes"         : "The most influential political club during the French Revolution of 1789. The period of its political ascendancy includes the Reign of Terror.",
                    "Delivered?"     : False,
                    "Method"        : "Update Stop",
                    "Phone Number"          : '9734032111',
                    "Bottles to Deliver"    : 3
            },
            {
                    "Name"                  : "Hugo De Vries",
                    "Salesforce Id"         : "ffas3251das",
                    "Address"               : "Netherlands",
                    "Bottles Dropped Off"   : 6,
                    "Bottles Picked Up"     : 4,
                    "Attachment"            : None,
                    "Notes"                 : "Dutch botanist and one of the first geneticists. He is known chiefly for suggesting the concept of genes.",
                    "Stop Number"           : 4,
                    "Delivered?"            : False,
                    "Method"                : "Update Stop",
                    "Phone Number"          : '9734032111',
                    "Bottles to Deliver"    : 3
                },

            ],
        "Date" : "2020-9-3",
        "Base Name" : "Deliveries"  
    }

x = requests.post(url, data = json.dumps(myobj),auth = HTTPBasicAuth(os.environ["SALESFORCE_USERNAME"],os.environ["SALESFORCE_PASSWORD"]))