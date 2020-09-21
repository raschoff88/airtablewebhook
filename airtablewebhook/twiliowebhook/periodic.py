import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import datetime
import re
from functools import reduce
from operator import concat
import numpy as np



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangowebsite.settings')



time=datetime.datetime.today()
#Twilio authetication
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_SID']
#create twilio client
client = Client(account_sid, auth_token)


default_message="""Hi from Tribeca Beverage, your delivery is for tomorrow. Please leave your bottles out! Please do not reply here, please email support@tribecabeverage.com"""
failed_to_send=[]

""" 

#Uses twilio to send message


"""


def send_text_message(number,sms):

    client.messages.create( 
                                from_='+16466812965',  
                                body=sms,
                                to=number
                            ) 

def text_message():
    #Google api scopes, authentication, and sheet
    scope = ['https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('secret_key.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key('1FIs7ymk0StQElddxbRWqa3aNZGS42HRAHDWRWBCVsQE').sheet1
    
    #default message edited on the google sheets
    sheet_message=sheet.acell('C2').value

    sent_messages=0	
    #collects all the numbers and specific messages on the list and reshapes them to be a rowcountx2 numpy array
    phone_message_list=sheet.range(f'A2:B{sheet.row_count}')
    phone_message_array=np.reshape(np.array(phone_message_list),(sheet.row_count-1,2))
    



    # passes through every number/custom message to send a text message
    for number_message in phone_message_array:


        if number_message[0].value:

            #filters only the digits in each cell and adjoins them.
            number=''.join(filter(str.isdigit,number_message[0].value))
            if int_like(number):
                if not number_message[1].value:
                    message=sheet_message
                else:
                    message=number_message[1].value
                try:
                        send_text_message(number,message)
                        
                        for database_entry in already_texted:
                            if number == database_entry[1]:
                                texted_twice.append(number+" ("+database_entry[2]+")")

                        c.execute(sql_insert_number_date,(number,f"{time.year},{time.month}.{time.day},{time.hour}"))



                        sent_messages+=1

                except:
                    failed_to_send.append(number)
            else:
                failed_to_send.append(number_message[0].value)


    #If any messages sent, sends an email to info@tribecabeverage.com giving a report.
    if sent_messages>0:
            try:
                message = Mail(
                    from_email='info@tribecabeverage.com',
                    to_emails='info@tribecabeverage.com',
                    subject='Text Message Update',
                    html_content=f"""Text Messages sent on  {time.month}/{time.day}/{time.year}, {time.hour}:{time.minute}:{time.second} to {sent_messages} numbers.
                        {'An error occured when texting the numbers: '+', '.join(failed_to_send)+'.' if failed_to_send else ''} 
                        {'The following numbers have been texted at least twice within the past 20 days: '+ ', '.join(texted_twice)+'.' if texted_twice else ''}""")
                sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
                response = sg.send(message)
            except:
                pass




    #clears and reformats sheet.			
    sheet.clear()
    sheet.update_acell('A1','Phone Numbers')
    sheet.update_acell('B1','Specific Message (sends default if no value)')
    sheet.update_acell('C1','Default Message')
    sheet.update_acell('C2',default_message)



def int_like(x):
    try:
        int(x)
        return True
    except:
        return False

def phone_format(phone_number):
    clean_phone_number = re.sub('[^0-9]+', '', phone_number)
    if clean_phone_number[0]=='1' and len(clean_phone_number)>10:
        clean_phone_number=clean_phone_number[1:]
    return clean_phone_number


if __name__=='__main__':
    text_message()


