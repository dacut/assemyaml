from __future__ import absolute_import, print_function
import boto3
from boto3.session import Session as Boto3Session
from botocore.client import Config
from json import loads as json_loads
from logging import getLogger
from six import string_types
from tempfile import NamedTemporaryFile
from traceback import format_exc
from zipfile import ZipFile
from assemyaml import run

log = getLogger("assemyaml.lambda")


def split_artifact_filename(s):
    """
    split_artifact_filename('artifact::filename') -> ('artifact', 'filename')

    Raises ValueError if "::" is not found.
    """
    index = s.index("::")
    return (s[:index], s[index+2:])


class InputArtifact(object):
    def __init__(self, input_artifact, boto_session):
        super(InputArtifact, self).__init__()
        self.input_artifact = input_artifact
        self.name = input_artifact["name"]
        self.location = input_artifact["location"]
        self.location_type = self.location["type"]
        self.artifact_file = None
        self.zip = None
        self.extracted_files = []
        self.boto_session = boto_session
        return

    def __del__(self):
        for file in self.extracted_files:
            file.close()

        if self.zip is not None:
            self.zip.close()

        if self.artifact_file is not None:
            self.artifact_file.close()

        return

    @property
    def url(self):
        if self.location_type != "S3":
            return "<unknown url format>"

        s3Loc = self.location["s3Location"]
        bucket = s3Loc["bucketName"]
        key = s3Loc["objectKey"]

        return "s3://%s/%s" % (bucket, key)

    def download(self):
        """
        ia.download() -> zipfile

        Downloads the input artifact archive and returns an open ZipFile
        handle to it.
        """
        if self.location_type != "S3":
            raise ValueError("Can't handle input artifact type %s" %
                             self.location_type)

        s3Loc = self.location["s3Location"]
        bucket = s3Loc["bucketName"]
        key = s3Loc["objectKey"]

        self.artifact_file = NamedTemporaryFile("w+b")

        s3 = self.boto_session.client(
            "s3", config=Config(signature_version="s3v4"))

        try:
            s3.download_fileobj(Bucket=bucket, Key=key,
                                Fileobj=self.artifact_file)
        except Exception as e:
            raise RuntimeError(
                "Unable to download input artifact %r (%s): %s" % (
                    self.name, self.url, e))

        self.zip = ZipFile(self.artifact_file, "r")
        return self.zip

    def get_file(self, filename):
        """
        ia.get_file(filename) -> fileobj

        Returns a temporary file with the contents of filename.
        """
        if self.zip is None:
            self.download()

        with self.zip.open(filename) as ifd:
            ofd = NamedTemporaryFile(mode="w+b")
            while True:
                data = ifd.read(65536)
                if not data:
                    break
                ofd.write(data)

        ofd.seek(0)

        self.extracted_files.append(ofd)
        return ofd


class CodePipelineJob(object):
    def __init__(self, event, context):
        super(CodePipelineJob, self).__init__()
        self.cp_job = event["CodePipeline.job"]
        self.cp_job_id = self.cp_job["id"]
        self.cp_data = self.cp_job["data"]
        self.cp_action_cfg = (self.cp_data.get("actionConfiguration", {})
                              .get("configuration", {}))
        self.cp_userparam_str = self.cp_action_cfg.get("UserParameters")
        self.cp_input_artifacts = self.cp_data["inputArtifacts"]
        self.cp_output_artifacts = self.cp_data["outputArtifacts"]

        creds = self.cp_data["artifactCredentials"]

        # Create a Boto3 session using the credentials provided by
        # CodePipeline, not the Lambda job, for processing artifacts.
        self.boto_session = Boto3Session(
            aws_access_key_id=creds["accessKeyId"],
            aws_secret_access_key=creds["secretAccessKey"],
            aws_session_token=creds["sessionToken"])

        # CodePipeline itself should be called using the default client.
        # We can't run this during unit tests -- Moto doesn't support it yet.
        skip_codepipeline = (
            event.get("TestParameters", {}).get("SkipCodePipeline"))
        if skip_codepipeline:
            self.codepipeline = None
        else:  # pragma: no cover
            self.codepipeline = boto3.client("codepipeline")

        # Parameters for running the transclusion
        self.default_input_filename = "assemble.yml"
        self.template_document_name = None
        self.resource_document_names = []
        self.local_tags = True
        self.format = "yaml"

        # File objects for the template and resources
        self.template_document = None
        self.resource_documents = []

        # Create a named temporary file for the output.
        self.output_temp = NamedTemporaryFile(mode="w+")

        return

    def run(self):
        self.create_input_artifacts()
        self.extract_user_parameters()
        self.extract_artifacts()
        self.transclude()
        self.write_output()
        return

    def create_input_artifacts(self):
        # The input artifacts, in order declared.
        self.input_artifacts = [InputArtifact(ia, self.boto_session)
                                for ia in self.cp_input_artifacts]

        # And by name
        self.input_artifacts_by_name = dict(
            [(ia.name, ia) for ia in self.input_artifacts])

        return

    def extract_user_parameters(self):
        # Decode the user parameters if specified.
        if self.cp_userparam_str:
            user_parameters = json_loads(self.cp_userparam_str)
            if not isinstance(user_parameters, dict):
                raise TypeError("Expected a JSON object for user parameters.")
        else:
            user_parameters = {}

        # What input artifacts have we seen?
        seen_artifacts = set()

        # Get the default input filename, if specified.
        self.default_input_filename = user_parameters.get(
            "DefaultInputFilename", "assemble.yml")

        # Get the template document name
        td = user_parameters.get("TemplateDocument")
        if td is not None:
            ia_name, _ = self.check_artifact_filename(td, "TemplateDocument")
            seen_artifacts.add(ia_name)
            self.template_document_name = td

        # And the resource document names
        rds = user_parameters.get("ResourceDocuments")
        if rds is not None:
            # Be lenient on input -- allow a single string instead of a list
            # of strings.
            if isinstance(rds, string_types):
                rds = [rds]

            for rd in rds:
                ia_name, _ = self.check_artifact_filename(
                    rd, "ResourceDocuments")
                seen_artifacts.add(ia_name)
                self.resource_document_names.append(rd)

        # Do we want local tag support?
        self.local_tags = user_parameters.get("LocalTags", True)

        # What format should we use for the output?
        self.format = user_parameters.get("Format", "yaml")
        if self.format not in ("json", "yaml",):
            raise ValueError(
                "Invalid output format '%s': valid types are 'json' and "
                "'yaml'" % self.format)

        # Name of the output file
        self.output_filename = user_parameters.get(
            "OutputFilename", "assemble.yml")

        # If any input artifacts are untouched, use them as the template or
        # additional resource documents.
        for ia in self.input_artifacts:
            if ia.name not in seen_artifacts:
                doc_name = ia.name + "::" + self.default_input_filename

                if self.template_document_name is None:
                    self.template_document_name = doc_name
                else:
                    self.resource_document_names.append(doc_name)

        if self.template_document_name is None:
            raise ValueError("No input artifact was specified as the "
                             "template file.")

        return

    def check_artifact_filename(self, doc_name, param_type):
        """
        cpj.check_artifact_filename(doc_name) -> (ia_name, filename)

        Make sure doc_name is in "artifact_name::filename" format, and
        that artifact_name is valid.
        """
        try:
            ia_name, filename = split_artifact_filename(doc_name)
        except ValueError:
            raise ValueError(
                "Invalid value for %s: expected input_artifact::filename: %s" %
                (param_type, doc_name))

        if ia_name not in self.input_artifacts_by_name:
            raise ValueError(
                "Invalid value for %s: unknown input artifact %s" %
                (param_type, ia_name))

        return ia_name, filename

    def extract_artifact(self, doc_name):
        ia_name, filename = split_artifact_filename(doc_name)
        ia = self.input_artifacts_by_name[ia_name]

        try:
            doc = ia.get_file(filename)
            doc.filename = doc_name
            return doc
        except Exception as e:
            raise RuntimeError(
                "While processing template document %s::%s from %s: %s" %
                (ia_name, filename, ia.url, e))

    def extract_artifacts(self):
        """
        Extract all input artifacts.
        """
        self.template_document = self.extract_artifact(
            self.template_document_name)

        for rdn in self.resource_document_names:
            self.resource_documents.append(self.extract_artifact(rdn))

    def transclude(self):
        result = run(self.template_document, self.resource_documents,
                     self.output_temp, self.local_tags)
        if result != 0:
            raise ValueError("Transclusion error -- see above messages for "
                             "details.")

        return

    def write_output(self):
        # Create the output ZipFile
        output_binary = NamedTemporaryFile(mode="w+b")
        output_zip = ZipFile(output_binary, "a")
        self.output_temp.seek(0)
        content = self.output_temp.read()
        output_zip.writestr(self.output_filename, content)
        output_zip.close()

        # Write the output artifact
        oa = self.cp_output_artifacts[0]
        s3loc = oa["location"]["s3Location"]
        bucket = s3loc["bucketName"]
        key = s3loc["objectKey"]
        output_binary.seek(0)
        s3 = self.boto_session.client(
            "s3", config=Config(signature_version="s3v4"))
        s3.put_object(Body=output_binary, Bucket=bucket, Key=key,
                      ServerSideEncryption="aws:kms")
        return

    def send_success(self):
        log.info("Notifying CodePipeline: put_job_success_result(%r)",
                 self.cp_job_id)
        if self.codepipeline:  # pragma: no cover
            self.codepipeline.put_job_success_result(jobId=self.cp_job_id)
        return

    def send_failure(self, message):
        log.info("Notifying CodePipeline: put_job_failure_result("
                 "%r, message=%r)", self.cp_job_id, message)
        if self.codepipeline:  # pragma: no cover
            self.codepipeline.put_job_failure_result(
                jobId=self.cp_job_id, failureDetails={
                    "type": "JobFailed",
                    "message": message,
                })
        return


def codepipeline_handler(event, context):
    """
    Lambda handler for CodePipeline events.
    """
    cpj = CodePipelineJob(event, context)

    try:
        cpj.run()

        # We're done.
        cpj.send_success()
        return
    except Exception as e:
        # Notify CodePipeline that we failed.
        log.error("Execution failed:%s", format_exc())
        cpj.send_failure("Unhandled exception: %s" % e)
