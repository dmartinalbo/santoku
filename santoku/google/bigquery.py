import pandas as pd

from typing import Dict, Any

from google.cloud import bigquery as bq
from google.oauth2 import service_account
from google.auth.credentials import Credentials
from ..aws.secrets_manager_handler import SecretsManagerHandler


class BigQueryHandler:
    """
    Manage Google BigQuery interactions, the simplest of which is to query a particular table.
    This makes use of the official BigQuery API. More information at
    https://googleapis.dev/python/bigquery/latest/index.html    
    """

    def __init__(self, **kwargs) -> None:
        """
        Base constructor. Use this to authenticate using Application Default Credentials.
        For alternative methods of authentication use the given class methods.

        Parameters
        ----------
        kwargs
            Additional arguments to be passed to google.cloud.bigquery.client.Client. If an argument
            is necessary but not provided, Google's API tries to infer it from Application Default
            Credentials.
        
        Raises
        ------
        google.auth.exceptions.DefaultCredentialsError
            Raised if credentials are not specified and the library fails to acquire default credentials.

        Notes
        -----
        Documentation for google.cloud.bigquery.client.Client in [1].
        More on authentication methods in [2] and [3].
        More on Application Default Credentials in [4].
        More on authentication via service account in [5].
        More on authentication as an end user in [6].
        To create a Credentials object, follow the google-auth guide in [7].

        References
        ----------
        [1] :
        https://googleapis.dev/python/bigquery/latest/generated/google.cloud.bigquery.client.Client.html
        [2] :
        https://cloud.google.com/bigquery/docs/authentication
        [3] :
        https://googleapis.dev/python/google-api-core/latest/auth.html#client-provided-authentication
        [4] :
        https://cloud.google.com/docs/authentication/production
        [5] :
        https://cloud.google.com/docs/authentication/production#obtaining_and_providing_service_account_credentials_manually
        [6] :
        https://cloud.google.com/docs/authentication/end-user
        [7] :
        https://google-auth.readthedocs.io/en/latest/user-guide.html#service-account-private-key-files
        """
        self.client = bq.Client(**kwargs)

    @classmethod
    def from_service_account_file(cls, file_name: str) -> BigQueryHandler:
        """
        Authenticate via service account credentials, passed as a JSON file.

        Parameters
        ----------
        file_name : str
            path to the file containing the credential information for a service account
        
        Notes
        -----
        The credentials file must look like this:
        ```
        {
            "type": "service_account",
            "project_id": "<project name>",
            "private_key_id": "<private key id>",
            "private_key": "<private key>",
            "client_email": "<service account email>",
            "client_id": "<client id>",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/<service account email>"
        }
        ```
        See [1] for instructions how to generate such file.

        References
        ----------
        [1] :
        https://cloud.google.com/iam/docs/creating-managing-service-account-keys#creating_service_account_keys
        """
        credentials = service_account.Credentials.from_service_account_file(file_name=file_name)
        return cls(credentials=credentials)

    @classmethod
    def from_service_account_info(cls, credential_info: Dict[str, str]) -> BigQueryHandler:
        """
        Authenticate via service account credentials, parsed as a dictionary.

        Parameters
        ----------
        credential_info: Dict[str, str]
            Credentials for a Google Cloud service account in dictionary form.

        Notes
        -----
        The credentials JSON must look like this:
        ```
        {
            "type": "service_account",
            "project_id": "<project name>",
            "private_key_id": "<private key id>",
            "private_key": "<private key>",
            "client_email": "<service account email>",
            "client_id": "<client id>",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/<service account email>"
        }
        ```
        See [1] for instructions how to generate such file.

        References
        ----------
        [1] :
        https://cloud.google.com/iam/docs/creating-managing-service-account-keys#creating_service_account_keys
        """
        credentials = service_account.Credentials.from_service_account_info(info=credential_info)
        return cls(credentials=credentials)

    @classmethod
    def from_aws_secrets_manager(cls, secret_name: str) -> BigQueryHandler:
        """
        Retrieve the necessary information to generate service account credentials from AWS Secrets Manager.
        Requires that AWS credentials with the appropriate permissions are located somewhere on the AWS credential chain in the local machine.
        
        Paramaters
        ----------
        secret_name : str
            Name or ARN for the secret containing the JSON needed for BigQuery authentication.
        
        Notes
        -----
        The retrieved secret must have the particular structure of the JSON file generated by the Google Cloud Console, which is associated with a service account.
        It looks like this:
        ```
        {
            "type": "service_account",
            "project_id": "<project name>",
            "private_key_id": "<private key id>",
            "private_key": "<private key>",
            "client_email": "<service account email>",
            "client_id": "<client id>",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/<service account email>"
        }
        ```
        See [1] for instructions how to generate such file.

        References
        ----------
        [1] :
        https://cloud.google.com/iam/docs/creating-managing-service-account-keys#creating_service_account_keys

        """
        secrets_manager = SecretsManagerHandler()
        credential_info = secrets_manager.get_secret_value(secrets_manager=secret_name)
        return cls(credential_info=credential_info)

    def run_query(self, query: str, **kwargs) -> bq.job.QueryJob:
        """
        Run a SQL query against datasets reachable from `self.project`. Returns a native datatype 
        QueryJob, which can be iterated or easily transformed to common types like pandas dataframe.

        Parameters
        ----------
        query : str
            SQL query to run on BigQuery
        kwargs : Dict[str, Any]
            Additional arguments for the google.cloud.bigquery.

        Notes
        -----
        More information on arguments for the query method: [1].
        More information on the QueryJob data type: [2].
        Convert QueryJob to pandas dataframe: [3].
        Convert QueryJob to pyarrow table: [4].

        References
        ----------
        [1] :
        https://googleapis.dev/python/bigquery/latest/generated/google.cloud.bigquery.client.Client.html#google.cloud.bigquery.client.Client.query

        [2] :
        https://googleapis.dev/python/bigquery/latest/generated/google.cloud.bigquery.job.QueryJob.html

        [3] :
        https://googleapis.dev/python/bigquery/latest/generated/google.cloud.bigquery.job.QueryJob.html?highlight=to_dataframe#google.cloud.bigquery.job.QueryJob.to_dataframe

        [4] :
        https://googleapis.dev/python/bigquery/latest/generated/google.cloud.bigquery.job.QueryJob.html?highlight=to_arrow#google.cloud.bigquery.job.QueryJob.to_arrow

        Returns
        -------
        google.cloud.bigquery.job.QueryJob
            Native datatype for BigQuery's query results. Can be converted to pd.DataFrame by calling
            to_dataframe() on it. More information in [2].
        """
        return self.client.query(query=query, **kwargs)
