#!/usr/bin/env python

import urllib

my_apikey = 'NXqJDwuUIkQ-wEQRo0cSbXyQKoQdmVZTb96zUxXz1r'

def send_sms(apikey, numbers, sender, message):
    data = urllib.urlencode({'apikey': apikey, 'numbers': numbers,
                                   'message': message, 'sender': sender})
    data = data.encode('utf-8')
    url = "https://api.txtlocal.com/send/?"
    f = urllib.urlopen(url, data)
    fr = f.read()
    return (fr)


resp = send_sms(my_apikey, '447788455444',
               'Telecare', 'Test')
print (resp)