"""
**Supports the sending of email via NHSMail and GMail**

Note
----
    GMail is currently deprecated

You can send patient information using the NHSMail server ``send.nhs.net`` using the credentials stored in
``SETTINGS["email"]["nhs_user"]`` and ``SETTINGS["email"]["nhs_pass"]`` in your process task::

    from dicomserver.myemail import nhs_mail

    nhs_mail(recipients=[doctor@nhs.uk, nurse@nhs.uk],
             subject="ProcessTask for Mouse,Anony ready for review",
             message="Please see attachment for the PDF of Mr Anony Mouse's results."
             attachments=["Mouse_Anony_Result.pdf"]
             )


During development and testing, emails are redirected to a debugging server ``@localhost:4000`` since it is likely
the developer will not have access to the NHS credentials.

Warnings
--------
    It is the dicomserver administrator's responsiblity to ensure the validity of the NHS credentials. The password will
    need to be regularly changed to meet NHS email security policy.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders

import PyPDF2
import imghdr
from mrs.tools.tools import is_under_test
from config.config import SETTINGS
from aide_sdk.logger.logger import LogManager


log = LogManager.get_logger()


def nhs_mail(recipients: list, subject: str, message: str, attachments: list = None, port=587):
    """
    Sends notification email to via NHS.net (for patient information)

    Parameters
    ----------
    port
    recipients
    subject
    message
    attachments

    Returns
    -------

    """

    user_name = SETTINGS['email']['nhs_user']
    password = SETTINGS['email']['nhs_pass']

    msg = construct_message(sender=user_name,
                            recipients=recipients, subject=subject, message=message, attachments=attachments)

    if is_under_test():
        s = smtplib.SMTP("localhost", 4000)  # local test server

    else:
        s = smtplib.SMTP("send.nhs.net", port)
        s.starttls()

        try:
            s.login(user_name, password)
        except smtplib.SMTPAuthenticationError:
            print('SMTPAuthenticationError')

    s.send_message(msg)
    s.quit()

    return msg


def construct_message(sender: str, recipients: list, subject: str, message: str, attachments: list):

    msg = MIMEMultipart()

    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)

    inline_image_string = ""

    if attachments:
        for att_fname in attachments:
            log.debug('Attaching:{att_fname}'.format(**locals()))
            if is_pdf(att_fname) or ('.html' in att_fname) or ('.xlsx' in att_fname) or ('.csv' in att_fname):
                att_file = open(att_fname, 'rb')
                if is_pdf(att_fname):
                    att = MIMEApplication(att_file.read(), _subtype='pdf')
                    att_file.close()
                    att.add_header('Content-Disposition', 'attachment', filename=att_fname)
                    msg.attach(att)
                elif '.html' in att_fname:
                    att = MIMEApplication(att_file.read(), _subtype='html')
                    att_file.close()
                    att.add_header('Content-Disposition', 'attachment', filename=att_fname)
                    msg.attach(att)
                elif '.xlsx' in att_fname:
                    part = MIMEBase('application', "octet-stream")
                    part.set_payload(att_file.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment; filename="CONCORD.xlsx"')
                    msg.attach(part)
                elif '.csv' in att_fname:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(att_file.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename=att_fname)
                    msg.attach(part)

            elif imghdr.what(att_fname) == 'png':
                inline_image_string += '<br><img src="cid:{}">'.format(str(att_fname))
                log.debug("Message:" + str(inline_image_string))
                png_file = open(att_fname, 'rb')
                msg_image = MIMEImage(png_file.read())
                png_file.close()
                msg_image.add_header('Content-ID', '<{}>'.format(str(att_fname)))
                msg.attach(msg_image)

    msg_text = MIMEText('{message}{inline_image_string}'.format(**locals()), 'html')
    # log.debug(msg_text)
    msg.attach(msg_text)

    return msg


def g_mail(recipients, subject, message, attachments: list = None):
    """
    Currently deprecated.

    Parameters
    ----------
    recipient
    subject
    message
    attachments
    """

    user_name = 'gsttphysics@gmail.com'
    password = 'Magnet06'

    s = smtplib.SMTP("smtp.gmail.com", 587)  #
    s.ehlo()
    s.starttls()
    msg = construct_message(sender=user_name,
                            recipients=recipients,
                            message=message,
                            subject=subject,
                            attachments=attachments)

    try:
        s.login(user_name, password)
    except Exception:
        raise
    s.send_message(msg)
    s.quit()


def is_pdf(fp: str) -> bool:
    f = open(fp, "rb")

    try:
        PyPDF2.PdfFileReader(f)
        return True

    except Exception as e:
        log.debug('Could not open {} as pdf. Assuming it is not pdf'.format(fp))
        return False

    finally:
        f.close()