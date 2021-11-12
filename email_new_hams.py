from datetime import date
from pathlib import Path
import logging
import os
from typing import Optional

from argparse import ArgumentParser
import pandas as pd
from tqdm import tqdm

from psrg_welcome.email import send_email
from psrg_welcome.qrz import get_authenticated_driver, find_email_from_callsign

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y/%m/%d %H:%M:%S"
)


def parse_args():

    parser = ArgumentParser()
    parser.add_argument(
        "--csv_fname", type=str, help="The CSV containing new ham information"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test rather than run against real data."
    )
    parser.add_argument(
        "--chromedriver_fname",
        type=str,
        default=None,
        help="The path to the Chrome driver.",
    )
    return parser.parse_args()


def fake_data() -> pd.DataFrame:
    """
    Generate some fake data for testing purposes.

    Returns
    -------
    pd.DataFrame
        A fake new ham dataset.
    """
    df = pd.DataFrame(
        {
            "Callsign": ["K7DRQ", "KI7RMU", "KD7DK"],
            "Name": ["Quentin", "Jack", "Doug"],
            "Class": ["Technician", "General", "Amateur Extra"],
            "Email": ["k7drq@psrg.org", "ki7rmu@psrg.org", "kd7dk@psrg.org"],
        }
    )

    return df.set_index("Callsign", drop=True)


def extract_from_csv(csv_fname: str) -> pd.DataFrame:
    """
    Pull callsigns and any listed emails from the monthly new ham CSV.

    Parameters
    ----------
    csv_fname : str
        The filename for the .csv file containing new ham details.
    
    Returns
    -------
    pd.DataFrame
        A dataframe containing new ham information.
    """

    # Read the file without a header; it's not always formatted correctly
    new_hams = pd.read_csv(csv_fname, header=None).rename(
        columns={0: "Callsign", 1: "Name", 12: "Class", 14: "Email"}
    )[["Callsign", "Name", "Class", "Email"]]

    # Throw out any header that's partway through the file
    new_hams = new_hams.loc[new_hams["Callsign"].str.len() < 7]

    # Replace pandas NaNs with native Nones
    new_hams = new_hams.where(new_hams.notna(), None)

    # Parse license classes
    new_hams["Class"] = new_hams["Class"].replace(
        to_replace={"T": "Technician", "G": "General", "E": "Amateur Extra"}
    )

    # Minor clean-up
    new_hams["Name"] = new_hams["Name"].str.title()
    new_hams["Email"] = (
        new_hams["Email"].where(new_hams["Email"].notna(), None).str.lower()
    )
    new_hams = new_hams.set_index("Callsign", drop=True)

    return new_hams


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
    for callsign, *_, email in tqdm(new_hams.itertuples()):
        if email is None:
            new_hams.loc[callsign] = find_email_from_callsign(callsign, driver=driver)

    return new_hams


if __name__ == "__main__":

    args = parse_args()

    local_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    chromedriver_fname = (
        args.chromedriver_fname
        if args.chromedriver_fname is not None
        else local_dir / "chromedriver"
    )

    # Load ham data
    if args.test:
        new_hams = fake_data()
    else:
        new_hams = extract_from_csv(args.csv_fname, args.test)
    known_emails = new_hams["Email"].notna().sum()

    # Fill in missing emails through QRZ
    logging.info(
        f"Found {len(new_hams)} new hams with {known_emails} known emails. "
        "Trying to find missing emails on QRZ."
    )
    new_hams = pull_missing_emails(new_hams, chromedriver_fname)

    # Confirm we want to email people
    logging.info(f"We now have {new_hams['Email'].notna().sum()} emails.")
    confirm = input("Enter 'yes' if you'd like to email these folk.\n> ")

    if confirm == "yes":

        # Load the email message
        with open(local_dir / "psrg_welcome/message.txt") as f:
            message = f.read()

        emailed = []

        # Email those for whom we have email addresses
        for call, name, class_, email in tqdm(
            new_hams.itertuples(), total=len(new_hams)
        ):

            if email is None:
                continue

            response = send_email(
                email,
                "Congrats on your amateur radio license !",
                message.format(name=name, call=call, class_=class_),
            )

            emailed.append(response.status_code == 202)

        # Save the list of folk we've emailed
        out_fname = local_dir / f"hams_emailed_{date.today().isoformat()}.csv"
        new_hams["Emailed ?"] = emailed
        new_hams.to_csv(out_fname)
        logging.info(f"List of emailed hams written to {out_fname}.")

    else:
        logging.info("User aborted.")
