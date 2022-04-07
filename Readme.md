# CORERE

## Description:
The main goal of the project is to make these verification tools cost-effective and easily accessible, so journals may implement and enforce more rigorous data policies. This will oblige researchers to in turn adopt more transparent practices and promote reproducible research of the highest quality and integrity throughout the scientific community. 

## Table of Contents:

* [Requirements](#Requirements)
* [Installation](#Installation)
* [Usage](#Usage)
* [Credits](#Credits)
* [License](#License)

## Requirements:
Python 3.9+ required

Docker is needed for deployment of notebook and proxy containers. It can be bypassed for development purposes.

Git is required for corere to manage user upload files and the versions. It is recommended to point Corere to a separate folder from the one used for other Git activities.

A postgres database is also required.

CentOS or RHEL is preferred, but is not required. Corere should also run on macOS.

## Installation:

#### The only installation option currently is a manual install. Docker based installation of the web application is not supported at this time.

### Bare Minimum:

Clone this repository:

```
git clone https://github.com/OdumInstitute/dataverse-corere
cd dataverse-corere
```

Create and activate a Python virtual environment:
```
python3 -m pip install virtualenv
virtualenv venv  
. ./venv/bin/activate
```

Install dependencies:
```
pip install -r requirements.txt -r requirements-dev.txt
```

For development, print emails to console by editing  `corere/settings/development.py`:
```
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
```

Edit `env.sample.sh` to setup application folders.  For example:
```
export DJANGO_LOG_DIRECTORY=/tmp/corere/logs
export CORERE_GIT_FOLDER=/temp/corere/git
export WHOLETALE_BASE_URL=stage.wholetale.org
```

Then create the directories:
```
mkdir -p /tmp/corere/logs /tmp/corere/git 
```

Edit `env.secret.sample.sh` to configure  
```
pen
export DJANGO_SECRET_KEY=<random key>
export SOCIAL_AUTH_GLOBUS_OAUTH2_KEY=<globus client id>
export SOCIAL_AUTH_GLOBUS_OAUTH2_SECRET=<globus secret>
export POSTGRES_USER=corere
export POSTGRES_PASSWORD=<postgres password>

export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_EMAIL=<your email>
export DJANGO_SUPERUSER_PASSWORD=<admin password>

export WHOLETALE_ADMIN_GIRDER_API_KEY=<your API key>
```

Optionally, run Postgres via Docker:
```
docker run -p 5432:5432 -e POSTGRES_USER=corere -e POSTGRES_PASSWORD=<postgres password> -d postgres
```

Source the config files:
```
. ./env.sample.sh
. ./env.secret.sample.sh
```

```
python3 manage.py migrate
python3 manage.py createsuperuser --noinput
python3 manage.py populate-info-from-wt
python3 manage.py initialize-wt --createlocal
```

Start Django server
```
python3 manage.py runsslserver
```

Once CORE2 is running, be sure got to the admin console `/admin/sites/site/` and change the default site to match your domain info. This will be used to populate the address in emails.

Configure CORE2 roles for the admin user:
* Goto https://localhost:8000/admin
* Select Users 
* Select admin
* Add all four roles

Invite yourself as a new Curator user:
* Goto https://localhost:8000/
* Select admin menu > Site Actions  > Invite Curator
* Look for link in logs (since email not configured)
* Note: we do this because the admin user should not be used for UI actions

In separate browser/private session:
* Open link
* Select "Register with Globus"

As admin user:
* Goto https://localhost:8000/admin
* Add all four roles to newly added user
* Check "Superuser status" 
* Save

As your user:
* Create a manuscript
* Upload manuscript files
* Create submission
* Upload submission files (e.g., scripts/data)
* Launch Notebook
* Optionally open dashboard.stage.wholetale.org to view progress


### Additional Functionality:

Register your application with Globus for auth (https://auth.globus.org/v2/web/developers/new). If you are using the local-container implementation via docker, you will need to add a block of redirect urls for Corere to use. The format is `http://localhost:[port]/oauth2/callback` . You will need to register port 50020 through 50039. You will also need to register `http://localhost/auth/complete/globus/` for new user registration. Also make sure when copying the client id, to use the one named `Client ID`.

[Insert docker info here]

Before going live in production, make sure to go into the admin interface and correct set your default Site. Go to sites, select the only object and change the domain and display name to match the server info

Note that the default configuration enables an sql-explorer for read-only queries. This uses the same user as write access, but with a read flag enabled. If you wish to make this more restrictive or remove it, see `https://django-sql-explorer.readthedocs.io/`.

## Usage

You will need to collect static files before running (and after updating these files) See https://docs.djangoproject.com/en/3.2/howto/static-files/ for more info.

Note that the `wholetale.py` file located in `corere/apps/wholetale/` has been built to be portable from the main application. If you are looking to integrate an application with Whole Tale, this might be a useful reference.

### First Run

Once the app is up and running, go to the Sites section of the admin console and change the names to match your current site. This is used mainly for email formatting.

Upon running the application for the first time, you will also want to set up an admin user. Use `manage.py createsuperuser` and then log in through `youraddress:yourport/admin` . You’ll need to use the admin console though to add these roles to the user so they can access all parts of the workflow. From the admin main page, go to “Users” and select your admin user. Then add these 4 roles: “Role Editor”, “Role Author”, “Role Curator”, “Role Verifier”.

## Credits
Odum Institute 

University of North Carolina at Chapel Hill

## License
(MIT)

Copyright 2019 Odum Institute

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
