import os
from typing import Optional

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import JavascriptException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service

from tqdm.notebook import tqdm
from time import sleep


def get_authenticated_driver(chromedriver_fname):

    username = os.environ.get("QRZ_USERNAME", "K7DRQ")
    password = os.environ.get("QRZ_PASSWORD")
    if password is None:
        raise ValueError("No QRZ_PASSWORD environment variable set.")

    service = Service(chromedriver_fname)

    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Chrome(options=options, service=service)

    driver.get("https://www.qrz.com/login")
    sleep(2)

    driver.find_element(by="id", value="username").send_keys(username)
    driver.find_element(by="id", value="username").send_keys(Keys.RETURN)
    sleep(2)

    driver.find_element(by="id", value="password").send_keys(password)
    driver.find_element(by="id", value="password").send_keys(Keys.RETURN)
    sleep(2)

    return driver


def find_email_from_callsign(
    callsign: str, driver: webdriver.chrome.webdriver.WebDriver
) -> Optional[str]:
    """
    Scrape QRZ for someone's email address.

    Parameters
    ----------
    callsign : str
        The person's callsign.
    driver : webdriver.chrome.webdriver.WebDriver
        An authenticated selenium webdriver.

    Returns
    -------
    Optional[str]
        Their email address, if found; None otherwise.
    """

    driver.get(f"https://www.qrz.com/db/{callsign}")

    try:
        driver.execute_script("showqem();")
        email = driver.find_element(by="id", value="qem").text
        return email.lower()
    except JavascriptException:
        return None


def pull_missing_emails(
    new_hams: pd.DataFrame, chromedriver_fname: str
) -> pd.DataFrame:
    """
    Attempt to pull missing email addresses from QRZ.

    Parameters
    ----------
    new_hams : pd.DataFrame
        A dataframe containing new ham callsigns and email addresses.
    chromedriver_fname : str
        The location of the Chromedriver matching your Chrome major version.

    Returns
    -------
    pd.DataFrame
        The same dataframe, hopefully with newer Nones and more email addresses.
    """

    # If there are no new emails to find, carry on
    if new_hams["Email"].isna().sum() == 0:
        return new_hams

    driver = get_authenticated_driver(chromedriver_fname)

    for callsign, email in tqdm(new_hams["Email"].to_dict().items()):
        if email is None:
            new_hams.loc[callsign] = find_email_from_callsign(callsign, driver=driver)

    return new_hams
