import os

import sendgrid
from python_http_client.client import Response


def send_email(to: str, subject: str, body: str) -> Response:
    """
    Send a plaintext email from secretary@psrg.org.

    Parameters
    ----------
    to : str
        The email address of the person receiving the email.
    subject : str
        The subject line for the email.
    body : str
        The full text to include in the email's body.

    Returns
    -------
    requests.models.Response
        The response to SendGrid's API call.
    """

    api_key = os.environ.get("SENDGRID_API_KEY")
    if api_key is None:
        raise ValueError("No SENDGRID_API_KEY environment variable set.")

    sg_client = sendgrid.SendGridAPIClient(api_key)

    email = sendgrid.helpers.mail.Mail(
        to_emails=to,
        from_email="secretary@psrg.org",
        subject=subject,
        plain_text_content=body,
    )

    response = sg_client.send(email)
    return response
