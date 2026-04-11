import pygeohash as gh
import uuid
import random

def to_geohash(lat, lon, precision=12):
    return gh.encode(lat, lon, precision=precision)


def from_geohash(geohash):
    return gh.decode(geohash)

def gen_l_dev_info():
    identifier = uuid.uuid4()
    hex_identifier = uuid.uuid4().hex[:16]
    random_integer = random.randint(1000000000, 9999999999)
    #resolution = "2277x1080"
    resolution = "1794x1080"
    return f"{hex_identifier};GLOBAL;2;{random_integer};{resolution};{identifier}"

