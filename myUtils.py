class Mailer(object):
    
    # if you don't want to pass these fix paramters to the class, fill them
    SMTP = '' ## FILL
    PORT = '' ## FILL 
    USER = '' ## FILL
    PWD = '' ## FILL
    SENDER = '' ## FILL
    RCPT = []
    BODY ='' ## FILL
    SUBJECT = '' ## FILL
    HTML = ""

    def __init__(self, smtp = SMTP, port = PORT, user = USER, pwd = PWD, sender = SENDER, rcpt = RCPT, body = BODY, subject = SUBJECT, html = HTML, files = []):
        self.__smtp = smtp
        self.__port = port
        self.__user = user
        self.__pwd = pwd
        self.__sender = sender
        self.__rcpt = rcpt
        self.__body = body
        self.__subject = subject
        self.__html = html
        self.__files = files

    def mail_send(self):
        """This is the method that actually send the email
        Todo: 

        """
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        from os.path import basename

        try:
            ## Instantiate smtplib.SMTP object NO SSL
            
            #print("Instantiate smtplib.SMTP object")
            ######__mail = smtplib.SMTP(self.__smtp, self.__port)
            #####        #
            ####### Connection and handshake
            ######print("Connection and handshake")
            ######__mail.ehlo()
            ######__mail.starttls()

            ####### Auth only if user is defined
            ######print("Auth only if user is defined")
            ######if self.__user:
            ######    __mail.login(self.__user, self.__pwd)
            
            ## Instantiate smtplib.SMTP object WITH SSL
            print("Connect")
            __mail = smtplib.SMTP_SSL(f'{self.__smtp}:{self.__port}')
            print("Login")
            __mail.login(self.__user,self.__pwd)
            print("Loggato!")


            # Create message/subject
            print("Create message/subject")
            msg = MIMEMultipart(self.__body)
            msg['Subject'] = self.__subject
            msg['To'] = self.__rcpt 
            msg['From'] = self.__sender
            if self.__html != "":
                part = MIMEText(self.__html, 'html')
                msg.attach(part)

            # Attachments!

            # Attachments!
            for f in self.__files or []:
                with open(f, "rb") as fil:
                    part = MIMEApplication(
                        fil.read(),
                        Name=basename(f)
                    )
                # After the file is closed
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
                msg.attach(part) 

            # Recipients are given as list even if only one (as string) was given
            print("Recipients are given as list even if only one (as string) was given")
            self.__rcpt = self.__rcpt \
            if isinstance(self.__rcpt, list) \
            else [self.__rcpt]

            # Actually send
            print("Actually send")
            print(__mail.sendmail(
                from_addr = self.__sender,
                to_addrs = self.__rcpt,
                msg = msg.as_string())) 
            __mail.close()
        except Exception as e:
            print(('Failed: '+ str(e)))
