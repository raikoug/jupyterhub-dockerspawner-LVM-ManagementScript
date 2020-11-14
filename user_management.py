import requests
import argparse
import os
import sys
from passgen import passgen
import crypt
from myUtils import Mailer # you will find this soon in the project
from jinja2 import Environment, FileSystemLoader
from random import shuffle
import pwd

parser = argparse.ArgumentParser(description='Gestione utenti per jupyterhub')

parser.add_argument('-a', '--add',
                     metavar='add',
                     type=str,
                     help='Path to csv file')

args = parser.parse_args()

input_path = args.add

if input_path:
    if not os.path.exists(input_path):
        print(f'File doesn't exists: {input_path}')
        sys.exit()
    
    lista = open(input_path, 'r').read()
    # i'm barbaric in my csv... not quotes.. i Know.. not the best..
    if "'" in lista or '"' in lista:
        print(f"CSV file is unsupported, check the template:\n")
	# I have a template to tell how I like them...
        print(open('/opt/jupyterhub/etc/jupyterhub/csv.template', 'r').read())
        sys.exit(1)

    lista = lista.split("\n")[1::]
    # I accept that each user could have more than 1 male seprated with ";"
    lista = [{'studente':el.split(',')[0], 'mail':el.split(',')[1]} for el in lista if el]
    mails = []
    allusers = []
    api_user_list = []
    
    for el in lista:
        userlist = [u.pw_name for u in pwd.getpwall()]
	
	# This could be seen as crazy... I take only alpha char of students
	# Then i shuffle them and create the username...
	# had not a better idea for duplicate "name surnames"
        protouser = el['studente']
        protouser = [b.lower() for b in protouser if b.isalpha()]
        while True:
            shuffle(protouser)
            username = "".join(protouser)
	    # check if username generated is not duplicated
            if username not in userlist:
                break
	
        print(f"Utente risulatante {username}")
	
        # Unix user creation
        password = passgen(50)
	# too long?
        encPass = crypt.crypt(password,"22")
	# encryption for useradd command on unix
        os.system("useradd -p "+encPass+f" {username}")

        ## user will be added as last thing to jupyterhub with a single api
        ## now MAILS
        file_loader = FileSystemLoader('templates')
        env = Environment(loader=file_loader)
	
	# I use a template to create html body of the mail
        template = env.get_template('base_send_password.html')
        output = template.render(username = username, password = password)

        mails = el['mail'].split(";")
        for email in mails:
            print(f"Creazione ed invio mail a {email}")
            mail = Mailer(rcpt = email, html = output)
            mail.mail_send()
	
	# DEBUG PURPOSE ONLY, this fill will store username password
        with open('utenze', 'a') as outfile:
            outfile.write(f"{username}:{password}\n")

    ## api to add users
    token = "YOUR_TOKEN"
    api_url = 'http://127.0.0.1:8000/hub/api'
    # body with list of users
    body = {"usernames": api_user_list,
            "admin": False
            }
    r = requests.post(api_url + '/users', headers={'Authorization': f"token {token}"}, json=body)
    if r.ok:
        print("DONE!!")
    else:
        print("Some error occurred")
    
