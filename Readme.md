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
Python 3.7+ required

Docker is required for deployment of notebook and proxy containers.

Git is required for corere to manage user upload files and the versions. It is recommended to point Corere to a separate folder from the one used for other Git activities.

CentOS or RHEL is preferred, but is not required. Corere should also run on macOS.

## Installation:
Install docker and git. 

Clone or download this repository. Customize the settings files as needed. Copy the sample env files and fill out there required attributes. 

Register your application with Globus for auth (https://auth.globus.org/v2/web/developers/new). You will need to add a block of redirect urls for Corere to use. The format is `http://localhost:[port]/oauth2/callback` . You will need to register port 50020 through 50039. Also make sure when copying the client id, to use the one named `Client ID`.

## Usage

Only local docker has been tested at this time.

## Credits
Odum Institute 

University of North Carolina at Chapel Hill

## License
(MIT)

Copyright 2019 Odum Institute

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
