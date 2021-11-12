import pandas as pd

from psrg_welcome.zips import local_zip_codes


def filter_local_hams(new_hams: pd.DataFrame) -> pd.DataFrame:
    """
    Return the subset of hams that are within 30km of Seattle downtown.

    Parameters
    ----------
    new_hams : pd.DataFrame
        A dataframe containing new ham callsigns and email addresses.

    Returns
    -------
    pd.DataFrame
        The same dataframe, with only hams with a local zip code.
    """

    return new_hams.loc[new_hams["Zip"].str[:5].isin(local_zip_codes)]


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
        columns={0: "Callsign", 1: "Name", 9: "Zip", 12: "Class", 14: "Email"}
    )[["Callsign", "Name", "Class", "Email", "Zip"]]

    # Throw out any header that's partway through the file
    new_hams = new_hams.loc[new_hams["Callsign"].str.len() < 7]

    # Keep only local hams
    new_hams = filter_local_hams(new_hams)

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
