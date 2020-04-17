import boto3
from typing import Any, Dict, List, Tuple
from botocore import exceptions


class SQSHandler:
    """
    Class to manage operations of Amazon Simple Queue Service (SQS).

    This class is intended to be run on AWS Glue jobs (Python Shell). SQS consists in hosted queues
    that allows sending and receiving messages. This class provides methods to interact with SQS
    queues and makes easy some usual operations. The connection to the SQS queues are done using the
    service class Client of the library boto3.

    """

    def __init__(self, region_name: str):
        """
        Instantiate the services classes.

        Parameters
        ----------
        region_name : str
            Region to which the AWS account is associated. All the queues to handle must be created
            in this region.

        """
        self.client = boto3.client("sqs", region_name=region_name)
        # Cache to store the url of each queue.
        self.queue_names_urls: Dict[str, str] = {}

    def queue_exist(self, queue_name: str) -> bool:
        """
        Check if a queue is created.

        Parameters
        ----------
        queue_name : str
            Name of queue.

        Returns
        -------
        bool
            True if the there is a queue with `queue_name` created.

        """
        try:
            response = self.client.get_queue_url(QueueName=queue_name)
        except exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AWS.SimpleQueueService.NonExistentQueue":
                return False
            else:
                raise
        return True

    def queue_is_fifo(self, queue_name: str) -> bool:
        """
        Check if a queue is of type FIFO.

        Parameters
        ----------
        queue_name : str
            Name of queue.

        Returns
        -------
        bool
            True if the queue is of type FIFO, False if it is standard.

        """
        return queue_name[-5:] == ".fifo"

    def get_queue_url_by_name(self, queue_name: str) -> str:
        """
        Return the url of the queue.

        Parameters
        ----------
        queue_name : str
            Name of queue.

        Returns
        -------
        str
            The url of the queue called `queue_name`.

        Notes
        -----
        The account url has the form: https://region_name.queue.amazonaws.com/account_number/queue_name
        More information on queue urls: [1]

        References
        ----------
        [1] :
        https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-general-identifiers.html

        """
        if self.queue_exist(queue_name=queue_name):
            queue_url = self.client.get_queue_url(QueueName=queue_name)["QueueUrl"]
        else:
            raise Exception("The queue `{}` does not exist.".format(queue_name))
        return queue_url

    def message_attributes_well_formed(
        self, message_attributes: Dict[str, Dict[str, str]]
    ) -> Tuple[bool, str]:
        """
        Check whether the message attributes are correct.

        Check if the message attributes are following the structure that AWS SQS requires. A boolean
        will be returned together with an error message in case it is not correctly structured.

        Parameters
        ----------
        message_attributes : Dict[str, Dict[str, str]]
            Message attributes to send.

        Returns
        -------
        Tuple[bool, str]
            True and an empty message will be returned if the message attributes are correclty
            formed. False and an error message explaining the error will be returned otherwise.

        Notes
        -----
        A message attribute can be of `DataType` Binary, Number and String.
        The `TypeValue` of the attribute must be StringValue if `DataType` is String or Number, and
        BinaryValue if `DataType` is Binary. StringListValues and BinaryListValues are
        options that should be accepted in the future but are not implemented yet. Strings are
        Unicode with UTF-8 binary encoding. Each message can have up to 10 message attributes.
        More information on the sqs message attributes: [1]

        References
        ----------
        [1] :
        https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-message-attributes.html

        """

        if len(message_attributes) > 10:
            error_message = "Messages can have up to 10 attributes."
            return (False, error_message)

        for _, attribute_content in message_attributes.items():

            if not isinstance(attribute_content, dict):
                error_message = "Each message attribute must be a dictionary containing 'DataType' and 'StringValue' arguments."
                return (False, error_message)

            if "DataType" not in attribute_content:
                error_message = "'DataType' argument is missing in message attribute."
                return (False, error_message)

            if attribute_content["DataType"] not in ["Binary", "Number", "String"]:
                error_message = "The supported types for 'DataType' argument are: Binary, Number and String."
                return (False, error_message)

            if (
                attribute_content["DataType"] == "String"
                and "StringValue" not in attribute_content
            ):
                error_message = "'StringValue' argument is required for message attributes of type String."
                return (False, error_message)

            if (
                attribute_content["DataType"] == "Number"
                and "StringValue" not in attribute_content
            ):
                error_message = "'StringValue' argument is required for message attributes of type Number."
                return (False, error_message)

            if (
                attribute_content["DataType"] == "Binary"
                and "BinaryValue" not in attribute_content
            ):
                error_message = "'BinaryValue' argument is required for message attributes of type Binary."
                return (False, error_message)

        return (True, "")

    def send_message(
        self,
        queue_name: str,
        message_body: str,
        message_attributes: Dict[str, Dict[str, Any]] = {},
    ) -> Dict[str, Any]:
        """
        Deliver a message to a SQS Queue.

        A message with `message_body` and optionally `message_attributes` will be sent to the queue
        named `queue_name`.

        Parameters
        ----------
        queue_name : str
            Name of the queue to send the message.
        message_body : str
            Body of of the message to be sent.
        message_attributes : Dict[str, Dict[str, Any]], optional
            Attributes of the message to send. Will be empty by default.

        Returns
        -------
        Dict[str, Any]
            A response containing information about the message sent. Among these information we
            can find the message id that identifies the message, and metadata containing the http
            status code.

        Raises
        ------
        AssertionError
            If the message argument is not correclty structured.

        See Also
        --------
        get_queue_url_by_name : this method retreives the queue url with the given queue name.
        message_attributes_well_formed : this methods check the message attributes given.

        Notes
        -----
        The maximum size that a message can have is 256KB (message body and attributes all together).

        """

        # Update the urls if not registered yet.
        if queue_name in self.queue_names_urls:
            queue_url = self.queue_names_urls[queue_name]
        else:
            queue_url = self.get_queue_url_by_name(queue_name)
            self.queue_names_urls[queue_name] = queue_url

        if message_attributes:
            # Check whether the message attributes are correctly structured.
            well_formed, error_message = self.message_attributes_well_formed(
                message_attributes=message_attributes
            )
            assert well_formed, error_message

            response = self.client.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body,
                MessageAttributes=message_attributes,
            )

        else:
            response = self.client.send_message(
                QueueUrl=queue_url, MessageBody=message_body
            )

        return response

    def send_message_batch(
        self, queue_name: str, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Deliver a list of messages to a SQS Queue.

        A list of batch request `entries` containing details of the messages will be sent to the
        queue named `queue_name`.

        Parameters
        ----------
        queue_name : str
            Name of the queue to send the batch of messages.
        entries : List[Dict[str, Any]]
            List of messages containing a unique message Id, a message body and message attributes
            optionally.

        Returns
        -------
        Dict[str, Any]
            A response containing information about all the sent messages. Among these information
            we can find the message id that identifies each message, and metadata containing the
            http status code of all the messages.

        Raises
        ------
        AssertionError
            If any message does not contain id or message body, if the ids are not unique, or if the
            message attributes are not correctly structured.

        See Also
        --------
        get_queue_url_by_name : this method retreives the queue url with the given queue name.
        message_attributes_well_formed : this method checks the message attributes given.

        Notes
        -----
        A batch can contain up to 10 messages.
        The maximum size that the batch of messages can have is 256KB, this means the sum of all
        messages (message body and attributes all together) cannot exceed 256KB.

        """
        assert entries, "The list of 'entries' cannot be emtpy."

        assert (
            len(entries) <= 10
        ), "The maximum number of messages allowed in a batch is 10."

        # Check if all the messages are have the required attributes and the message attributes are
        # correctly structured.
        entries_ids = []
        for entry in entries:

            assert "Id" in entry, "'Id' attribute is required for each message."
            entries_ids.append(entry["Id"])

            assert (
                "MessageBody" in entry
            ), "'MessageBody' attribute is required for each message."

            if "MessageAttributes" in entry:
                well_formed, error_meesage = self.message_attributes_well_formed(
                    entry["MessageAttributes"]
                )
                assert well_formed, error_meesage

        # Check the message ids are unique along the batch.
        assert len(entries_ids) == len(
            set(entries_ids)
        ), "'ID' attribute must be unique along all the messages."

        # Update the urls if not registered yet.
        if queue_name in self.queue_names_urls:
            queue_url = self.queue_names_urls[queue_name]
        else:
            queue_url = self.get_queue_url_by_name(queue_name)
            self.queue_names_urls[queue_name] = queue_url

        response = self.client.send_message_batch(QueueUrl=queue_name, Entries=entries)
        return response

    def receive_message(self, queue_name: str) -> Dict[str, Any]:
        """
        Retrieves multiple messages from the SQS Queue.

        Parameters
        ----------
        queue_name : str
            Name of the queue to receive a message.

        Returns
        -------
        Dict[str, Any]
            A response containing information about all the received messages. Among these
            information we can find the message id that identifies each message, the receipt
            handle used to delte the message, and the content of the message such as the message
            body and message attributes.

        Raises
        ------
        AssertionError
            If any message does not contain id or message body, if the ids are not unique, if the
            message attributes are not correctly structured.

        See Also
        --------
        get_queue_url_by_name : this method retreives the queue url with the given queue name.
        message_attributes_well_formed : this method checks the message attributes given.

        Notes
        -----
        The maximum number of messages we can receive in each call is 10.
        There is an attribute called visibility timeout, that is the time that SQS keep a message
        invisible after it has been received once. After that period of time the message will be
        visible again. This is why removing the message after receiving it is so important.

        References
        ----------
        [1] :
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.receive_message

        """
        # Update the urls if not registered yet.
        if queue_name in self.queue_names_urls:
            queue_url = self.queue_names_urls[queue_name]
        else:
            queue_url = self.get_queue_url_by_name(queue_name)
            self.queue_names_urls[queue_name] = queue_url

        response = self.client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10
        )
        return response

    def delete_message(self, queue_name: str, receipt_handle: str) -> None:
        """
        Remove a message from the queue.

        A message with the `receipt_handle` will be deleted from the queue with name `queue_name`.

        Parameters
        ----------
        queue_name : str
            Name of the queue to delete the message from.
        receipt_handle : str
            Identifier obtained from receiving the message to delete.

        Returns
        -------
        None

        See Also
        --------
        get_queue_url_by_name : this method retreives the queue url with the given queue name.

        Notes
        -----
        You must always receive a message before you can delete it (you can't put a message into the
        queue and then recall it.
        The difference between the receipt handle and the message id is that the first one is
        associated with the action of receiving the message and not the message itself.
        More information on the receipt handle: [1]

        References
        ----------
        [1]:
        https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-general-identifiers.html

        """
        # Update the urls if not registered yet.
        if queue_name in self.queue_names_urls:
            queue_url = self.queue_names_urls[queue_name]
        else:
            queue_url = self.get_queue_url_by_name(queue_name)
            self.queue_names_urls[queue_name] = queue_url

        self.client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        return None
