"""Utilities for working with Azure blob storage"""
import re
import io

from azure.storage.blob import BlobServiceClient


class AzureBlobStore(object):
    """
    Represents a Blob of storage on Azure

    Methods
    -------
    The following are wrapped utilities for Azure storage:
        - read
        - listdir
        - write
    """

    def _blob_service_client(self, account_name, sas_token):

        return BlobServiceClient(
            "{account}.blob.core.windows.net".format(account=account_name),
            sas_token,
        )

    @classmethod
    def _split_url(cls, url):
        """
        see: https://docs.microsoft.com/en-us/azure/storage/common/storage-dotnet-shared-access-signature-part-1  # noqa: E501
        abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken
        """
        if match := re.match(
            r"abs://(.*)\.blob\.core\.windows\.net\/(.*)\/(.*)\?(.*)$", url
        ):
            return {
                "account": match[1],
                "container": match[2],
                "blob": match[3],
                "sas_token": match[4],
            }
        else:
            raise Exception("Invalid azure blob url '{0}'".format(url))

    def read(self, url):
        """Read storage at a given url"""
        params = self._split_url(url)
        output_stream = io.BytesIO()
        blob_service_client = self._blob_service_client(params["account"], params["sas_token"])
        blob_client = blob_service_client.get_blob_client(params['container'], params['blob'])
        blob_client.download_blob().readinto(output_stream)
        output_stream.seek(0)
        return [line.decode("utf-8") for line in output_stream]

    def listdir(self, url):
        """Returns a list of the files under the specified path"""
        params = self._split_url(url)
        blob_service_client = self._blob_service_client(params["account"], params["sas_token"])
        container_client = blob_service_client.get_container_client(params["container"])
        return list(container_client.list_blobs(params["blob"]))

    def write(self, buf, url):
        """Write buffer to storage at a given url"""
        params = self._split_url(url)
        blob_service_client = self._blob_service_client(params["account"], params["sas_token"])
        blob_client = blob_service_client.get_blob_client(params['container'], params['blob'])
        blob_client.upload_blob(data=buf, overwrite=True)
