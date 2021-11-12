from datetime import date
from pathlib import Path
import logging
import os

from argparse import ArgumentParser
import pandas as pd
from tqdm import tqdm

from psrg_welcome.arrl_file import combine_with_previously_emailed, extract_from_csv
from psrg_welcome.email import send_email
from psrg_welcome.qrz import pull_missing_emails

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y/%m/%d %H:%M:%S"
)


def parse_args():

    parser = ArgumentParser()
    parser.add_argument(
        "--new_arrl_csv",
        type=str,
        help="The filename of the CSV containing new ham information.",
    )
    parser.add_argument(
        "--previously_emailed_csv",
        default="hams_welcomed.csv",
        type=str,
        help=(
            "The file output by this application containing information about "
            "people previously emailed, so we don't email them twice."
        ),
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
            "Zip": ["12345", "12345", "12345"],
        }
    )

    return df.set_index("Callsign", drop=True)


if __name__ == "__main__":

    args = parse_args()

    # Ensure a CSV filename is passed
    if args.new_arrl_csv is None and not args.test:
        raise ValueError("You need to provide a --new_arrl_csv.")

    # Set up the local directory and location of the Chromedriver
    local_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    chromedriver_fname = (
        args.chromedriver_fname
        if args.chromedriver_fname is not None
        else local_dir / "chromedriver"
    )

    # Load ARRL's ham data file
    if args.test:
        new_hams = fake_data()
    else:
        new_hams = extract_from_csv(args.new_arrl_csv)

    # Try loading previously-emailed data
    new_hams = combine_with_previously_emailed(new_hams, args.previously_emailed_csv)

    # Fill in missing emails through QRZ
    not_emailed = new_hams["Emailed ?"].isna()
    known_emails = new_hams["Email"].notna() & not_emailed
    logging.info(
        f"Found {not_emailed.sum()} new hams with {known_emails.sum()} known emails. "
        "Trying to find missing emails on QRZ."
    )
    new_hams = pull_missing_emails(new_hams, chromedriver_fname)

    # Confirm we want to actually email people
    known_emails = new_hams["Email"].notna() & not_emailed
    logging.info(f"We now have {known_emails.sum()} people to email.")
    confirm = input("Enter 'yes' if you'd like to email these folk.\n> ")

    if confirm == "yes":

        # Load the email message
        with open(local_dir / "psrg_welcome/message.txt") as f:
            message = f.read()

        to_email = new_hams.loc[
            new_hams["Email"].notna() & new_hams["Emailed ?"].isna()
        ]

        # Email those for whom we have email addresses
        for call, name, class_, email, _, emailed_previously in tqdm(
            to_email.itertuples(), total=len(to_email)
        ):

            # Pass on those without an email address, or if we've already emailed them
            if (email is None) or (emailed_previously is not None):
                continue

            # For those we have an email address, send the email
            response = send_email(
                email,
                "Congrats on your amateur radio license !",
                message.format(name=name, call=call, class_=class_),
            )

            if response.status_code == 202:
                new_hams.loc[call, "Emailed ?"] = date.today().isoformat()

        # Save the list of folk we've emailed
        out_fname = local_dir / f"hams_welcomed.csv"
        new_hams = new_hams.dropna(subset=["Emailed ?"])
        new_hams.to_csv(out_fname)
        logging.info(f"List of emailed hams written to {out_fname}.")

    else:
        logging.info("User aborted.")
