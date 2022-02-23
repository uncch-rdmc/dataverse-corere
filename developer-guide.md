# CORERE Developer Guide

## Description:
Additional info on development decisions. This document is a work in progress, being added to as parts of the system are touched.

## Table of Contents:

* [Communications](#Communications)

## Communications:

This section is a catch-all to discuss the ways in which users are communicated to by the system. Aside from standard page html, there are other methods used:
- Banner messages using the messages framework https://docs.djangoproject.com/en/3.2/ref/contrib/messages/
- Notifications using the django-notifications-hq package https://pypi.org/project/django-notifications-hq/
- Emails using the django-templated-email package
- Account creation emails that come from the django-invitations package

For all these message types, we are using django translations to store our messaging external to the views. While this is somewhat tedious, it'll allow non-technical staff to edit messaging and will scale well when we support other languages.

There is a standard structure to follow with these translation strings: [object]\_[messageDescription]\_[type(optional)]\_[messageTarget(optional)].

As an example: manuscript_noFiles_error tells us: 
1. The message sent to the user is related to the manuscript object
2. The reason for the message is due to a lack of files
3. The message is intended to be used as an error message.

Note that type is optional and is intended for use when there are different messages about the same topic depending on the communication type.

To add new messages translations:
1. Add your message the above format to the django code
2. Run "django-admin makemessages -l en --no-wrap". You might have to add the corere project folder to your `PYTHONPATH`.
3. Refer to the django.po file, and find your string. makemesages has probably tried to guess a message for it, and it is wrong. Delete the guessed message as well as the "fuzzy" comment.
4. Write your own string
5. Run "django-admin compilemessages" so the strings will show up while operating the system.

### Invitation:
We currently use a fork of django-invitations (1.9.3) with minor change to pass the key forward to signup as we use it when creating an initial user.

Note that if you want to change the subject or any other text other than body, it'll need to be done in the fork. Unless you want to try to fix why subject isn't as flexible in the library ([start here](https://github.com/bee-keeper/django-invitations/blob/9069002f1a0572ae37ffec21ea72f66345a8276f/invitations/adapters.py#L34)).

