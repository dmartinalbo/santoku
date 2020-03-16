import os
import requests
import pytest
import json
from ..salesforce.connection import SalesforceConnection


class TestConnect:
    @classmethod
    def teardown_method(self):
        # Clean the sandbox each time a testcase is executed.
        sc = SalesforceConnection(
            auth_url=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )
        response = json.loads(sc.do_request(method="GET", path="sobjects/Contact"))
        obtained_contacts = response["recentItems"]
        for obtained_contact in obtained_contacts:
            sc.do_request(
                method="DELETE", path="sobjects/Contact", id=obtained_contact["Id"]
            )

    def test_wrong_credentials(self):
        sc = SalesforceConnection(
            auth_url=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
            username="wrong_user",
            password="wrong_password",
            client_id="wrong_client_id",
            client_secret="wrong_client_secret",
        )
        with pytest.raises(requests.exceptions.RequestException) as e:
            sc.do_request(
                method="POST", path="sobjects/Contact", payload={"Name": "Alice Bob"}
            )

    def test_contact_insertion(self):
        sc = SalesforceConnection(
            auth_url=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )

        # Insert 3 Contacts that do not exist. [OK]
        contact_payloads = [
            {
                "FirstName": "Randall D.",
                "LastName": "Youngblood",
                "Email": "randall@example.com",
            },
            {
                "FirstName": "Amani Cantara",
                "LastName": "Fakhoury",
                "Email": "amani@example.com",
            },
            {
                "FirstName": "Mika-Matti",
                "LastName": "Ridanpää",
                "Email": "mika-matti.ridanpaa@example.com",
            },
        ]
        for contact_payload in contact_payloads:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
        assert response

        # Insert a Contact that already exist with a new email. [OK]
        contact_payloads[0]["Email"] = "youngblood@example.com"
        response = sc.do_request(
            method="POST", path="sobjects/Contact", payload=contact_payloads[0],
        )
        assert response

        # Insert a Contact that already exist. [NO]
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )
            assert response

    def test_contact_query(self):
        sc = SalesforceConnection(
            auth_url=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )

        # Read 0 Contacts with sobjects.
        response = json.loads(sc.do_request(method="GET", path="sobjects/Contact"))
        obtained_contacts = response["recentItems"]
        assert not obtained_contacts
        # Read 0 Contacts with SOQL.
        response = json.loads(sc.do_query_with_SOQL("SELECT Name from Contact"))
        assert response["totalSize"] == 0

        # Insert 2 Contacts.
        contact_payloads = [
            {
                "FirstName": "Angel",
                "LastName": "Collins",
                "Email": "angel@example.com",
            },
            {"FirstName": "June", "LastName": "Ross", "Email": "june@example.com",},
        ]
        for contact_payload in contact_payloads:
            sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
        # Read the 2 Contacts inserted with sobjects. [OK]
        response = json.loads(sc.do_request(method="GET", path="sobjects/Contact"))
        obtained_contacts = response["recentItems"]
        assert len(obtained_contacts) == 2
        obtained_names = []
        obtained_ids = []
        for obtained_contact in obtained_contacts:
            obtained_names.append(obtained_contact["Name"])
            obtained_ids.append(obtained_contact["Id"])
        # When getting all the contacts with sobjects, the field Name appears with the format:
        # "LastName, FirstName"
        expected_names = ["Collins, Angel", "Ross, June"]
        for expected_name in expected_names:
            assert expected_name in obtained_names
        # When getting all the contacts with SOQL, the field Name appears with the usual format:
        # "FirstName LastName"
        # Read the 2 Contacts inserted with SOQL. [OK]
        expected_names = ["Angel Collins", "June Ross"]
        response = json.loads(sc.do_query_with_SOQL("SELECT Id, Name from Contact"))
        assert response["totalSize"] == 2
        obtained_contacts = response["records"]
        obtained_names = []
        obtained_ids = []
        for obtained_contact in obtained_contacts:
            obtained_names.append(obtained_contact["Name"])
            obtained_ids.append(obtained_contact["Id"])
        for expected_name in expected_names:
            assert expected_name in obtained_names

        # Read a specific Contact with sobjects. [OK]
        response = json.loads(
            sc.do_request(method="GET", path="sobjects/Contact", id=obtained_ids[0],)
        )
        obtained_contact = response
        # When getting a specific contact with sobjects, the field Name appears with the usual format:
        # "FirstName LastName"
        assert obtained_contact["Name"] == obtained_names[0]
        # Read a specific contact with SOQL. [OK]
        response = json.loads(
            sc.do_query_with_SOQL("SELECT Name from contact WHERE Name = 'June Ross'")
        )
        assert response["totalSize"] == 1
        obtained_contacts = response["records"]
        assert obtained_contacts[0]["Name"] == "June Ross"
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name from contact WHERE Id = '{}'".format(obtained_ids[0])
            )
        )
        assert response["totalSize"] == 1
        obtained_contacts = response["records"]
        assert obtained_contact["Name"] == obtained_names[0]

        # Query a contact that does not exists with sobjects. [NO]
        with pytest.raises(requests.exceptions.RequestException) as e:
            sc.do_request(
                method="GET", path="sobjects/Contact", id="WRONGID",
            )
        # Query a contact that does not exists with SOQL. [OK]
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Name from contact WHERE Name = 'Nick Mullins'"
            )
        )
        assert response["totalSize"] == 0

    def test_contact_modification(self):
        sc = SalesforceConnection(
            auth_url=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )

        # Insert 2 Contacts.
        contact_payloads = [
            {"FirstName": "Ramon", "LastName": "Evans", "Email": "ramon@example.com",},
            {"FirstName": "Janis", "LastName": "Holmes", "Email": "janis@example.com",},
        ]
        for contact_payload in contact_payloads:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Modify an existing contact's FirstName and LastName. [OK]
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name from Contact WHERE Name = 'Ramon Evans'"
            )
        )
        obtained_contacts = response["records"]
        contact_payload = {"FirstName": "Ken", "LastName": "Williams"}
        response = sc.do_request(
            method="PATCH",
            path="sobjects/Contact",
            id=obtained_contacts[0]["Id"],
            payload=contact_payload,
        )
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name from Contact WHERE Id = '{}'".format(
                    obtained_contacts[0]["Id"]
                )
            )
        )
        obtained_contacts = response["records"]
        assert obtained_contacts[0]["Name"] == "Ken Williams"

        # Modify an existing contact's Email. [OK]
        contact_payload = {"Email": "ken@example.com"}
        response = sc.do_request(
            method="PATCH",
            path="sobjects/Contact",
            id=obtained_contacts[0]["Id"],
            payload=contact_payload,
        )
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name, Email from Contact WHERE Id = '{}'".format(
                    obtained_contacts[0]["Id"]
                )
            )
        )
        obtained_contacts = response["records"]
        assert obtained_contacts[0]["Name"] == "Ken Williams"
        assert obtained_contacts[0]["Email"] == "ken@example.com"

        # It seems that a compound field is not modifiable
        # Modify an existing contact's Name. [NO]
        contact_payload = {"Name": "Marie Rogers"}
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = sc.do_request(
                method="PATCH",
                path="sobjects/Contact",
                id=obtained_contacts[0]["Id"],
                payload=contact_payload,
            )

        # Modify a Contact that does not exist. [NO]
        contact_payload = {"FirstName": "Marie"}
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = sc.do_request(
                method="PATCH",
                path="sobjects/Contact",
                id="WRONGID",
                payload=contact_payload,
            )

    def test_contact_deletion(self):
        sc = SalesforceConnection(
            auth_url=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )

        # Insert 2 Contacts.
        contact_payloads = [
            {
                "FirstName": "Brian",
                "LastName": "Cunningham",
                "Email": "brian@example.com",
            },
            {
                "FirstName": "Julius",
                "LastName": "Marsh",
                "Email": "julius@example.com",
            },
        ]
        for contact_payload in contact_payloads:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Delete an existing Contact. [OK]
        response = json.loads(sc.do_query_with_SOQL("SELECT Id, Name from Contact"))
        obtained_contacts = response["records"]
        obtained_contacts_names = []
        obtained_contacts_ids = []
        for obtained_contact in obtained_contacts:
            obtained_contacts_names.append(obtained_contact["Name"])
            obtained_contacts_ids.append(obtained_contact["Id"])
        sc.do_request(
            method="DELETE", path="sobjects/Contact", id=obtained_contacts_ids[0],
        )
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Name from Contact WHERE Name = '{}'".format(
                    obtained_contacts_names[0]
                )
            )
        )
        assert response["totalSize"] == 0
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Name from contact WHERE Name = '{}'".format(
                    obtained_contacts_names[1]
                )
            )
        )
        assert response["totalSize"] == 1

        # Delete a Contact that does not exist. [NO]
        with pytest.raises(requests.exceptions.RequestException) as e:
            sc.do_request(
                method="DELETE", path="sobjects/Contact", id="WRONGID",
            )
