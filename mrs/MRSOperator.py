from aide_sdk.inference.aideoperator import AideOperator
from aide_sdk.model.operatorcontext import OperatorContext
from aide_sdk.model.resource import Resource
from aide_sdk.utils.file_storage import FileStorage
from pydicom._dicom_dict import DicomDictionary
from pydicom.datadict import keyword_dict

from mrs.dicom.study import Study
from mrs.processing.MRSTask import MRSTask
from mrs.tools.tools import check_valid_mrs


class MRSOperator(AideOperator):
    """
    MRSOperator class

    This class is used to perform MRS processing, and then create a report and archive it to PACS.
    """

    def process(self, context: OperatorContext) -> OperatorContext:

        mrs_study = self._build_dicomserver_study(context)

        if check_valid_mrs(context):
            mrs_task = MRSTask(mrs_study)
            mrs_task.process()

    def _build_dicomserver_study(self, context: OperatorContext) -> Study:

        for series in context.origin.series:
            for image in series.images:
                pass
