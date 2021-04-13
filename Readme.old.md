# CORE-RE

![Dataverse](https://user-images.githubusercontent.com/48030162/59379352-62f3e180-8d24-11e9-93b6-a7b28767bfb9.png)

## Description:
The main goal of the project is to make these verification tools cost-effective and easily accessible, so journals may implement and enforce more rigorous data policies. This will oblige researchers to in turn adopt more transparent practices and promote reproducible research of the highest quality and integrity throughout the scientific community. 

#### Note: This project is undergoing architectural changes, the information in this document is likely to be out of date.

## Table of Contents:

* [Requirements](#Requirements)
* [Installation](#Installation)
* [Usage](#Usage)
* [Contributing](#Contributing)
* [Credits](#Credits)
* [License](#License)
* [Future Work](#Future)


## Requirements:
Python 3.7+ required

Anaconda is suggested but not required.

Kubernetes and Docker is required for running binderhub.
(https://binderhub.readthedocs.io/en/latest/)

@andreyodum/core2 jupyterlab extension to use with jupyterhub (installed automatically)

R and R server (automatically installed by binderhub)

CentOS or RHEL is preferred, but is not required.

## Installation:

The CORE-RE project consits of three components: CORE-RE server, binderhub server, and gitlab server.

The latter two can be downloaded and set up using the following sites:

https://about.gitlab.com/
https://binderhub.readthedocs.io/en/latest/


### Setting up CORE-RE server

It is recommended that you run this (and all) python projects inside a virtual environment. See this page for more info https://docs.python.org/3/tutorial/venv.html .

Install the latest version of Python 3 if you haven't already.

Run the following command:
```python
pip install -r requirements.txt
```

Copy `env.sample.sh` to `env.sh`. Open `env.sh` and change parameters accordingly. See the file for more info on the parameters.

You will also need to install a postgres database or use the commented sqlite database section of your settings file.

Before running django, run `. env.sh` to export the variables to your environment.

Finally, run your django manage.py to start the django server (change the settings path to a production file if needed):
```python
python manage.py runserver --settings=corere.settings.development
```

### Setting up Binderhub server


#### Minikubernetes Instruction


Follow the guide found here:
https://github.com/jupyterhub/binderhub/blob/master/CONTRIBUTING.md

or use the following (This guide assumes you are on CentOS):

```bash
sudo apt install socat -y
```

##### Download and install kubectl
```bash
curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
```

```bash
chmod +x ./kubectl
```

```bash
sudo mv ./kubectl /usr/local/bin/kubectl
```

##### Install VirtualBox
Download the latest version of virtualbox at https://www.virtualbox.org/wiki/Downloads

##### Install Minikube
```bash
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 \
  && chmod +x minikube
```

Add minikube executable to the path
```
sudo install minikube /usr/local/bin
```

Start Minikube 
```bash
minikube start
```

Clone the binderhub repository to your local computer and cd into it.
```bash
git clone https://github.com/jupyterhub/binderhub
cd binderhub
```

Install helm to manage installating JupyterHub and Binderhub on cluster.
```bash
curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get | bash
```

Initialize helm in minikube.
```bash
helm init
```

Add JupyterHub helm charts repo
```bash
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
helm repo update
```

Install BinderHub and its development requirements
```bash
python -m pip install -e . -r dev-requirements.txt
```


Copy the following into your binderhub directory. 
File Path: binderhub/testing/minikube/binderhub_config.py

```python
# config file for testing with minikube-config.yaml
import subprocess
try:
    minikube_ip = subprocess.check_output(['minikube', 'ip']).decode('utf-8').strip()
except (subprocess.SubprocessError, FileNotFoundError):
    minikube_ip = '192.168.1.100'

c.BinderHub.hub_url = 'http://{}:30123'.format(minikube_ip)
c.BinderHub.hub_api_token = 'aec7d32df938c0f55e54f09244a350cb29ea612907ed4f07be13d9553d18a8e4'
c.BinderHub.use_registry = False
c.BinderHub.build_namespace = 'binder-test'

### The command below is important to allow other hosts to access
### Feel free to change this setting to only allow access from specific domain
c.BinderHub.tornado_settings.update({
        'headers': {
            'Access-Control-Allow-Origin': '*',
        }
})
```

Install JupyterHub in minikube 
```bash
./testing/minikube/install-hub
```

Set up docker daemon
```bash
eval $(minikube docker-env)
```

Start BinderHub with the testing config file
```bash
python -m binderhub -f testing/minikube/binderhub_config.py
```

Visit http://localhost:8585

Your binderhub should now be set up on the server.

#### Kubernetes Instructions

Follow the guide found at:
https://binderhub.readthedocs.io/en/latest/create-cloud-resources.html


### Setting up GitLab Server

Follow instructions found on https://about.gitlab.com/install/ to set up your own gitlab. There is not really anything you need to do except to get the private token. 

## Usage



## Future work

User Roles

Detection 


## Contributing
Thank you for your interest in contributing to CORE-RE Project!  We welcome any contribution from anybody. If you have any questions, please feel free to reach out to us. If you want to add a feature, please create a fork, add the feature, and create a pull request. If you have an issue, please search if there are existing similar issues using the search bar in the issues tab. If an existing open issue exists, contribute to it. Otherwise, please create a new issue.

### Code Coverage
To see code coverage:
```bash
coverage run --source='.' manage.py test corere
coverage report --omit="*prototype*"
```

## Credits
Odum Institute 

University of North Carolina at Chapel Hill

## License
(MIT)

Copyright 2019 Odum Institute

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
