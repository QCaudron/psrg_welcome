# A welcome from PSRG

This application emails new hams a "welcome to radio" email and points them in the general 
direction of the PSRG.

## How it works

You pass in a CSV file emailed by the ARRL coordinator, containing the information around new ham 
licenses. This file contains new allocated callsigns, first names, and a small number of email 
addresses.

We pull info from QRZ to attempt to fill in missing email addresses. No QRZ subscription is 
required; we simply scrape the website ( and are thus subject to rate limits, which I believe 
are 100 hits per 24h period ). 

We then email all those we have an email address for. You can see the 
[message we send here](psrg_welcome/message.txt). Emails are sent through Sendgrid using their
free tier, which limits us to 100 emails per month.


## Getting started

### Installing dependencies

First, ensure you have the Python dependencies installed : 
```
pip install -r requirements.txt
```

Then, you need the [Chromedriver](https://chromedriver.chromium.org/downloads) that corresponds 
with your version of Google Chrome. This application uses headless Selenium to scrape QRZ for
emails, so you need to supply this downloadable. Either put it in the root directory, or point
to it using the `--chromedriver_fname` command line argument.


### Environment variables 

Then, set some environment variables :

- `QRZ_USERNAME` is the callsign you use to sign into QRZ ( `K7DRQ` for instance ).
- `QRZ_PASSWORD` is your QRZ password.
- `SENDGRID_API_KEY` is the API key with permissions to send emails with Sendgrid.


### Run the script

Run the script, telling it where the new ham CSV is :

```
python email_new_hams.py --csv_fname path/to/new_ham_stuff.csv
```

## Options

The `email_new_hams.py` script has a few options; see them all with `python email_new_hams.py --help`.

- `--csv_fname <FILENAME>` : the location of the CSV containing new ham information, as sent by ARRL.
- `--chromedriver_fname <FILENAME>` : the location of the Chromedriver executable.
- `--test` : run the script on some fake data, rather than on an actual CSV of new ham information. 