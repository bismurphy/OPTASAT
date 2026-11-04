import os
import requests
import datetime
import csv

#ID_number must be an int which is the sat id number.
#25544 for ISS, for example.
#acceptable_age is a date which indicates the oldest a TLE may be.
#if TLE is older than this, we will try to fetch it.
def get_tle(ID_number, acceptable_age):
    ID_number = str(ID_number)
    if not os.path.exists(ID_number + ".tle"):
        web_retrieve_tle(ID_number)
    else:
        with open(ID_number + ".tle") as f:
            data = list(csv.DictReader(f))[0]
        epoch = datetime.datetime.fromisoformat(data['EPOCH']).astimezone(datetime.timezone.utc)
        # existing ephemeris is older (lower time) than the acceptable time
        if epoch < acceptable_age:
            web_retrieve_tle(ID_number)
    # TLE has been retrieved if needed, now open it
    with open(ID_number + ".tle") as f:
        data = list(csv.DictReader(f))[0]
        return data

def web_retrieve_tle(ID_number):
    ID_number = str(ID_number)
    session = requests.session()
    url = f"http://www.celestrak.org/NORAD/elements/gp.php?CATNR={ID_number}&FORMAT=csv"
    page = session.get(url)
    with open(ID_number + ".tle","w") as f:
        f.write(page.text)
    return

if __name__ == "__main__":
    three_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
    print(get_tle(25544), three_days_ago)
