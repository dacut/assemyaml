from __future__ import print_function
from assemyaml.lambda_handler import codepipeline_handler
from boto3.session import Session as Boto3Session
from json import dumps as json_dumps
from moto import mock_s3
from logging import getLogger, WARNING
from os import listdir
from os.path import dirname
from random import randint
from six import iteritems, next
from six.moves import cStringIO as StringIO, range
from string import ascii_letters, digits
from testfixtures import LogCapture
from unittest import TestCase
from uuid import uuid4
from yaml import dump as yaml_dump, load as yaml_load
from zipfile import ZipFile


_keyspace = ascii_letters + digits
def random_keyname(length=7):  # noqa: E302
    return "".join([
        _keyspace[randint(0, len(_keyspace) - 1)] for i in range(length)])


log = getLogger("test_lambda")


@mock_s3
class TestLambda(TestCase):
    def setUp(self):
        self.bucket_name = "codepipeline-us-west-2-00000000000"
        self.pipeline_name = "hello"
        self.boto3 = Boto3Session(region_name="us-west-2")
        for logname in ("botocore", "s3transfer"):
            getLogger(logname).setLevel(WARNING)

    def artifact_dict(self, artifact_name, key):
        """
        tl.artifact_dict(artifact_name, key) -> dict

        Returns a dictionary for an artifact suitable for inclusion in a
        CodePipeline Lambda event. Details on this are here:
        http://docs.aws.amazon.com/codepipeline/latest/userguide/actions-invoke-lambda-function.html
        """
        return {
            "location": {
                "s3Location": {
                    "bucketName": self.bucket_name,
                    "objectKey": key,
                },
                "type": "S3",
            },
            "revision": None,
            "name": artifact_name,
        }

    def create_input_artifact(self, artifact_name, contents):
        # Zip the contents up into an S3 object
        zip_binary = StringIO()
        with ZipFile(zip_binary, "w") as zip_file:
            for key, value in iteritems(contents):
                zip_file.writestr(key, value)

        s3_key = "%s/%s/%s.zip" % (
            self.pipeline_name, artifact_name, random_keyname())

        s3 = self.boto3.resource("s3", region_name="us-west-2")
        bucket = s3.Bucket(self.bucket_name)
        obj = bucket.Object(s3_key)
        obj.put(Body=zip_binary.getvalue())

        return self.artifact_dict(artifact_name, s3_key)

    def lambda_event(self, input_artifacts, output_artifact,
                     template_document=None,
                     resource_documents=None, default_input_filename=None,
                     local_tags=None):

        user_params = {}
        if template_document is not None:
            user_params["TemplateDocument"] = template_document

        if resource_documents is not None:
            user_params["ResourceDocuments"] = resource_documents

        if default_input_filename is not None:
            user_params["DefaultInputFilename"] = default_input_filename

        if local_tags is not None:
            user_params["LocalTags"] = local_tags

        action_cfg = {"configuration": {"FunctionName": "Lambda"}}
        if user_params:
            action_cfg["configuration"]["UserParameters"] = (
                json_dumps(user_params))

        creds = {
            "secretAccessKey": "",
            "sessionToken": "",
            "accessKeyId": "",
        }

        data = {
            "actionConfiguration": action_cfg,
            "inputArtifacts": input_artifacts,
            "outputArtifacts": [output_artifact],
            "artifactCredentials": creds,
        }

        job = {
            "id": str(uuid4()),
            "accountId": "000000000000",
            "data": data
        }

        test_params = {
            "SkipCodePipeline": True
        }

        return {
            "CodePipeline.job": job,
            "TestParameters": test_params,
        }

    def run_doc(self, filename):
        s3 = self.boto3.resource("s3", region_name="us-west-2")
        bucket = s3.Bucket(self.bucket_name)
        bucket.create()

        with open(filename, "r") as fd:
            log.info("Running Lambda test on %s" % filename)
            doc = yaml_load(fd)
            input_artifacts = []

            for artifact in doc["InputArtifacts"]:
                name = artifact["Name"]
                contents = {}

                for filename, data in iteritems(artifact.get("Files", {})):
                    if isinstance(data, (list, dict)):
                        data = yaml_dump(data)

                    contents[filename] = data

                input_artifacts.append(
                    self.create_input_artifact(name, contents))

            output_artifact = doc["OutputArtifact"]

        output_filename, expected_content = next(
            iteritems(output_artifact["Files"]))
        expected_content = yaml_load(expected_content)

        output_artifact_name = output_artifact.get("Name", "Output")
        output_artifact_key = "%s/%s/%s.zip" % (
            self.pipeline_name, output_artifact_name, random_keyname())
        output_artifact = self.artifact_dict(
            output_artifact_name, output_artifact_key)

        event = self.lambda_event(input_artifacts, output_artifact)

        codepipeline_handler(event, None)
        result_obj = s3.Object(self.bucket_name, output_artifact_key)
        result_zip = result_obj.get()["Body"].read()

        with ZipFile(StringIO(result_zip), "r") as zf:
            with zf.open(output_filename, "r") as fd:
                result = yaml_load(fd)

        self.assertEquals(result, expected_content)

    def test_documents(self):
        directory = dirname(__file__) + "/lambda"
        for filename in listdir(directory):
            if not filename.endswith(".yml"):
                continue

            self.run_doc(directory + "/" + filename)

    def test_bad_userparams(self):
        event = self.lambda_event([], self.artifact_dict("Output", "key"))
        event["CodePipeline.job"]["data"]["actionConfiguration"]\
            ["configuration"]["UserParameters"] = "{])}"

        with LogCapture() as l:
            codepipeline_handler(event, None)

        self.assertIn("Expecting property name", str(l))

        event = self.lambda_event([], self.artifact_dict("Output", "key"))
        event["CodePipeline.job"]["data"]["actionConfiguration"]\
            ["configuration"]["UserParameters"] = "[]"

        with LogCapture() as l:
            codepipeline_handler(event, None)

        self.assertIn("Expected a JSON object for user parameters", str(l))
