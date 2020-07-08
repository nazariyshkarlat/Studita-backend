from smtp.html_mail import send_html_mail

sender_email = "education.app.developers@gmail.com"
password = 'f<V/]%Vd;sW;@\\CJChPE`K47Xwz,>VK6^r}-q*vL\"EpKE6&Sd:aRD;,pv?yx~~q34GwMXWz+[ca[(nq]@nPfn{#hm:rAhY9W;Bvw'


def send_mail(receiver_email):
    send_html_mail("Добро пожаловать в Studita!", 'smtp/html/mail.html', receiver_email, sender_email, password)
    print("Mail on " + receiver_email + " is sent!")