import numpy as np
from aide_sdk.inference.aideoperator import AideOperator
from aide_sdk.model.operatorcontext import OperatorContext
from aide_sdk.model.resource import Resource
from aide_sdk.utils.file_storage import FileStorage
from pydicom._dicom_dict import DicomDictionary
from pydicom.datadict import keyword_dict

from mrs.processing.MRSTask import MRSTask
from mrs.tools.tools import check_valid_mrs


class MRSOperator(AideOperator):

    def process(self, context: OperatorContext) -> OperatorContext:

        if check_valid_mrs(context):
            mrs_task = MRSTask()
            mrs_task.process()
