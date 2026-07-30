import os
import requests
import datetime
import csv

#ID_number must be an int which is the sat id number.
#25544 for ISS, for example.
#acceptable_age tells how old a tle can be before we choose to re-fetch
def get_tle(ID_number, acceptable_age = 3):
    ID_number = str(ID_number)
    if not os.path.exists(ID_number + ".tle"):
        web_retrieve_tle(ID_number)
    else:
        with open(ID_number + ".tle") as f:
            data = list(csv.DictReader(f))[0]
        epoch = datetime.datetime.fromisoformat(data['EPOCH']).astimezone(datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        # convert age in seconds to fraction of days
        tle_age = (now - epoch).total_seconds()/86400
        print(tle_age)
        if tle_age > acceptable_age:
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
    print(get_tle(25544))
