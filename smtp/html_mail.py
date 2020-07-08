import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_html_mail(subject, body, to_addr, from_addr, password):
    """Send an HTML email using the given subject, body, etc."""

    # Create message container - the correct MIME type is multipart/alternative here!
    message = MIMEMultipart('alternative')
    message['subject'] = subject
    message['To'] = to_addr
    message['From'] = from_addr

    # Record the MIME type dict/html.
    with open(body, 'r', encoding='utf-8') as f:
        html_string = f.read()
    html_body = MIMEText(html_string, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    message.attach(html_body)

    # The actual sending of the e-mail
    # server = smtplib.SMTP('smtp.gmail.com:587')
    with smtplib.SMTP("smtp.gmail.com", 25) as server:
        server.set_debuglevel(1)
        server.ehlo()
        server.starttls()
        server.login(from_addr, password)
        server.sendmail(
            from_addr, to_addr, message.as_string()
        )