import os
import pycurl
from http import HTTPStatus
import json
import zlib
from .utils import gen_l_dev_info

#user_agent = "grindr3/25.15.2.140001;140001;Free;Android 13;Pixel 2;Google"
user_agent = "grindr3/26.9.2.164876 ;164876 ;Free;Android 13;Pixel 2;Google"
user_agent_header = "user-agent: " + user_agent
cookie_file = ""

def set_cookie_file_location(file: str):
    global cookie_file
    cookie_file = file

def process_response_data(response_data, debug):
    response_data = b"".join(response_data)
    if debug:
        print("response_data:", response_data)
    if not response_data:
        return {}
    try:
        decompressed_response = zlib.decompress(response_data, zlib.MAX_WBITS | 16)
        if debug:
            print("decompressed_response:", decompressed_response)
    except zlib.error:
        decompressed_response = response_data
    try:
        return json.loads(decompressed_response)
    except:
        #print("ERROR response:", decompressed_response)
        print("ERROR response: writing to err.html")
        with open("err.html", "wb") as f:
            f.write(decompressed_response)
        return {}

def request_headers(content_type, dev_info, auth_token=None):
    #L-Locale: de_DE
    #Accept-language: de-DE
    headers = [
        "accept: application/json",
        "accept-encoding: gzip",
        "accept-language: en-US",
        "connection: Keep-Alive",
        "content-type: " + content_type,
        "host: grindr.mobi",
        f"l-device-info: {dev_info}",
        "l-locale: en_US",
        "l-time-zone: Europe/Berlin",
        "requirerealdeviceinfo: true",
        user_agent_header,
    ]
    if auth_token is not None:
        headers.append("authorization: Grindr3 " + auth_token)
    return headers

def default_headers(dev_info, auth_token=None):
    content_type = "application/json; charset=UTF-8"
    return request_headers(content_type, dev_info, auth_token)

def generic_request(request_type, url, configureCb, dev_info, auth_token=None, debug=False):
    response_data = []

    c = pycurl.Curl()
    c.setopt(c.URL, url)
    if debug:
        c.setopt(pycurl.VERBOSE, 1)
    c.setopt(c.CUSTOMREQUEST, request_type)
    c.setopt(c.COOKIEJAR, cookie_file)
    c.setopt(c.COOKIEFILE, cookie_file)
    # For debugging/capturing only! Huge security hole while on.
    c.setopt(pycurl.SSL_VERIFYPEER, 0)
    c.setopt(pycurl.SSL_VERIFYHOST, 0)
    headers = default_headers(dev_info, auth_token)
    c.setopt(c.HTTPHEADER, headers)
    if debug:
        print("HEADERS:\n", "\n".join(headers))
    configureCb(c)

    def handle_response(data):
        response_data.append(data)

    c.setopt(c.WRITEFUNCTION, handle_response)
    c.perform()
    response_code = c.getinfo(c.RESPONSE_CODE)
    if debug:
        print("RESPONSE CODE:", response_code)
    elif response_code != 200:
        response_text = HTTPStatus(response_code).phrase
        print(f"E: Server response: {response_code} ({response_text}) to", request_type, url)
    c.close()

    return process_response_data(response_data, debug)

def url_from_path(path, parameters=None):
    url = "https://grindr.mobi" + path
    if parameters:
         url += "?" + "&".join([key + "=" + parameters[key] for key in parameters])
    return url

def generic_post(path, request_body, dev_info, auth_token=None, debug=False):
    def configure(c):
        if request_body is not None:
            data_json = json.dumps(request_body)
            c.setopt(c.POSTFIELDS, data_json)
            if debug:
                print("POSTFIELDS:\n", data_json)
        #else: ?? Check how to send empty post: do nothing or set POSTFIELDS to NONE?
    url = url_from_path(path)
    return generic_request("POST", url, configure, dev_info, auth_token, debug)

def post_file(path, filename, content_type, dev_info, auth_token=None, debug=False):
    filesize = os.path.getsize(filename)
    with open(filename, 'rb')as fin:
        filedata = fin.read()
    assert filesize == len(filedata)
    def configure(c):
        headers = request_headers(content_type, dev_info, auth_token)
        print(headers)
        c.setopt(c.HTTPHEADER, headers)
        c.setopt(c.POSTFIELDSIZE, filesize)
        c.setopt(c.POSTFIELDS, filedata)
    url = url_from_path(path)
    return generic_request("POST", url, configure, dev_info, auth_token, debug)

def generic_get(path, request_parameters, dev_info, auth_token=None, debug=False):
    def configure(c):
        pass
    url = url_from_path(path, request_parameters)
    return generic_request("GET", url, configure, dev_info, auth_token, debug)

def generic_put(path, request_body, dev_info, auth_token=None, debug=False):
    def configure(c):
        if request_body is not None:
            data_json = json.dumps(request_body)
            c.setopt(c.POSTFIELDS, data_json)
            if debug:
                print("POSTFIELDS:\n", data_json)
    url = url_from_path(path)
    return generic_request("PUT", url, configure, dev_info, auth_token, debug)

def generic_delete(path, dev_info, auth_token=None, debug=False):
    def configure(c):
        pass
    url = url_from_path(path)
    return generic_request("DELETE", url, configure, dev_info, auth_token, debug)
