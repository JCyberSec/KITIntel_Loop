#  _  _____ _____  __        __                               
# | |/ /_ _|_   _| \ \      / / __ __ _ _ __  _ __   ___ _ __ 
# | ' / | |  | |    \ \ /\ / / '__/ _` | '_ \| '_ \ / _ \ '__|
# | . \ | |  | |     \ V  V /| | | (_| | |_) | |_) |  __/ |   
# |_|\_\___| |_|      \_/\_/ |_|  \__,_| .__/| .__/ \___|_|   
#                                      |_|   |_|              
#
'''
KIT Wrapper

Command line tool to enable easier use of WMC Global KIT API

For API key please contact WMC Global :: https://www.wmcglobal.com/contact

Author :: Jake
''' 
__version__ = '2.7.13'


# Import Table
from copy import deepcopy
from typing import Dict, Any, List
import argparse
import errno
import json
import os
import pandas
import re
import requests
import traceback
import uuid
import sys
import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

## Global Config options
# Load the configuration file
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
except Exception as e:
    logging.error("Failed to parse config file. Make sure the file is a valid JSON structure")
    raise e
    sys.exit()

# Extract configurations with defaults
proxies = config.get("proxies", {})
proxy_auth = config.get("proxy_auth", {})
cert = config.get("cert", None)  # Default to None if not set
verify = config.get("verify", True)  # Default to True if not set

# Create a session object
session = requests.Session()

# Update the session with proxy settings if they exist
if proxies:
    session.proxies.update(proxies)

# Update the session with authenticated proxy settings if they exist
if proxy_auth:
    session.proxies.update(proxy_auth)



# Content download location
Default_Download_Location = os.getcwd()

# KIT URL base endpoint
URL_Endpoint = 'https://api.phishfeed.com/KIT/v1'

VAILD_KEYWORDS = {
    "datetime": "datetime",
    "content": "content",
    "file.filename": "file.filename",
    "file.filetype": "file.filetype",
    "file.md5": "file.md5",
    "file.sha256": "file.sha256",
    "file.size": "file.size",
    "file.ssdeep": "file.ssdeep",
    "file.UUID": "file.UUID",
    "filename": "file.filename",
    "filetype": "file.filetype",
    "fullfilename": "fullfilename",
    "file.fullfilename": "fullfilename",
    "kit.filetype": "kit.filetype",
    "kit.kitname": "kit.kitname",
    "kit.md5": "kit.md5",
    "kit.sha256": "kit.sha256",
    "kit.size": "kit.size",
    "kit.ssdeep": "kit.ssdeep",
    "kit.UUID": "kit.UUID",
    "md5": "file.md5",
    "scroll_id": "scroll_id",
    "sha256": "file.sha256",
    "size": "file.size",
    "size_filter": "size_filter",
    "ssdeep": "file.ssdeep",
    "UUID": "UUID",
}


# Function to make a GET request using the session
def make_get_request(target_url):
    response = session.get(
        target_url,
        cert=cert,
        verify=verify
    )
    return response

# Function to make a POST request using the session
def make_post_request(target_url, data):
    # Retrieve headers from the config or use session defaults
    headers = config.get("headers", {})
    response = session.post(
        f"{URL_Endpoint}{target_url}",
        data=data,
        cert=cert,
        verify=verify,
        headers=headers
        )
    return response


# Function to access content API
def content(uuidInput):
    try:
        data = {}
        data['UUID'] = uuidInput
        # POST request to the endpoint
        response = make_post_request('/content', json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            # extract the content download URL
            # Override headers for this specific request
            request_headers = {}
            # Make the request with overridden headers
            response = make_get_request(result['download_url'])
            if response.status_code == 200:
                # If saving to file
                return (response.text)
            else:
                # Error
                # traceback.print_exc()
                return ("ERROR\t- Failed to download content for {}".format(uuidInput))
        elif response.status_code == 403:
            return  ("ERROR\t- Forbidden")
        else:
            # Error
            return ("ERROR\t- Failed to request content for {}".format(uuidInput))
    except Exception as e:
        # Error
        return ("ERROR\t- Failed to parse {}".format(uuidInput))

def cross_join(left, right):
    new_rows = [] if right else left
    for left_row in left:
        for right_row in right:
            temp_row = deepcopy(left_row)
            for key, value in right_row.items():
                temp_row[key] = value
            new_rows.append(deepcopy(temp_row))
    return new_rows


def flatten_list(data):
    for elem in data:
        if isinstance(elem, list):
            yield from flatten_list(elem)
        else:
            yield elem


def json_to_dataframe(data_in):
    def flatten_json(data, prev_heading=''):
        if isinstance(data, dict):
            rows = [{}]
            for key, value in data.items():
                rows = cross_join(rows, flatten_json(value, prev_heading + '.' + key))
        elif isinstance(data, list):
            rows = []
            for i in range(len(data)):
                [rows.append(elem) for elem in flatten_list(flatten_json(data[i], prev_heading))]
        else:
            rows = [{prev_heading[1:]: data}]
        return rows

    return pandas.DataFrame(flatten_json(data_in))


def recursive_get(value: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    current_point = value
    for key in path:
        try:
            current_point = current_point[key]
        except KeyError:
            return default
    return current_point


# Function to search KIT
def search(searchInput, filterInput=None, numberInput=None, dateGTEInput='5y', uniqueInput=None, formatInput=None, downloadInput=None, dateLTEInput=None):
    data = {}
    # Split search parameters
    search_array = searchInput.split(' IN ')
    # Regex pattern to split keyword and search variable
    # Fine first occournace of : and then capture the rest of the string
    pattern = r"([^:]*)(.*)"

    # Loop through the search input
    for i in range(len(search_array)):
        try:
            # Extract the regex results
            matchObj = re.search(pattern, search_array[i])
            # Check there are hits from the regex
            if matchObj:
                # Strip away a space in the keyword
                keyword = str(matchObj.group(1)).replace(' ', '')
                # Strip char 1 from the value which will always be a ':' due to the regex
                value = str(matchObj.group(2)[1:])
                # Check to ensure the keyword is able to be searched
                if keyword in VAILD_KEYWORDS.keys():
                    if keyword == 'scroll_id':
                        data[keyword] = int(value)
                    else:
                        keyword = VAILD_KEYWORDS[keyword]
                        data[keyword] = value
                else:
                    # Error
                    return ("ERROR\t- '{}' - Unknown search term. Please try again".format(keyword))
                    exit()
            else:
                # Error 
                return ("ERROR\t- Invalid key:value pair")
        except Exception as e:
            # Error
            logging.error(e)
            return ("ERROR\t- Ensure search is valid with keyword:search_term")
    # Parse filter argument
    if filterInput:
        filterItems = []
        for keyword in filterInput.split(','):
            keyword = keyword.strip()
            if keyword in VAILD_KEYWORDS.keys():
                keyword = VAILD_KEYWORDS[keyword]
                filterItems.append(keyword)
            else:
                # Error
                return ("ERROR\t- '{}' - Unknown filter term. Please try again".format(keyword))
                exit()

        data["filter"] = filterItems
        # filterData = (filterItems)

    # Parse number argument
    if numberInput:
        data["page_size"] = int(numberInput)

    # Parse date argument
    if dateLTEInput:
        date = {}
        date["gte"] = str(dateGTEInput)
        date["lte"] = str(dateLTEInput)
        data["datetime_filter"] = date
    elif dateGTEInput:
        date = {}
        date["gte"] = 'now-' + str(dateGTEInput)
        data["datetime_filter"] = date
        
    logging.info("API Search: {}".format(data))
    try:
        # POST request to the endpoint
        response = make_post_request('/search', json.dumps(data))
    except Exception as e:
        # Error
        return ("ERROR\t- Failed search POST")

    if response.status_code == 200:
        parsed = json.loads(response.text)
        # Parse unique argument
        if uniqueInput:
            keyword = uniqueInput.strip()
            if keyword in VAILD_KEYWORDS.keys():
                keyword = VAILD_KEYWORDS[keyword]
                uniqueItem = VAILD_KEYWORDS[keyword].split('.')
                logging.info(parsed["results"])
                parsed["results"] = list({ recursive_get(each,uniqueItem) : each for each in parsed["results"] }.values())
                parsed["unique_count"] = len(parsed["results"])
            else:
                # Error
                return ("ERROR\t- '{}' - Unknown unique term. Please try again".format(keyword))
                exit()

        content = json.dumps(parsed)
        return content

    elif response.status_code == 403:
        return ("ERROR\t- Forbidden")
    else:
        # Error
        logging.error(response.text)
        return ("ERROR\t- Failed search")
