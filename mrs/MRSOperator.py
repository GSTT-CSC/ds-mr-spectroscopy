from aide_sdk.inference.aideoperator import AideOperator
from aide_sdk.model.operatorcontext import OperatorContext

from mrs.dicom.study import Study
from mrs.processing.MRSTask import MRSTask
from mrs.tools.tools import check_valid_mrs
from aide_sdk.logger.logger import LogManager
logger = LogManager.get_logger()


class MRSOperator(AideOperator):
    """
    MRSOperator class

    This class is used to perform MRS processing, and then create a report and archive it to PACS.
    """

    def process(self, context: OperatorContext) -> OperatorContext:
        """
        Process the MRS task.
        :param context:
        :return: OperatorContext
        """
        mrs_study = Study(study_dir=context.origin.file_path)

        if check_valid_mrs(mrs_study):
            logger.info(f'Study {mrs_study} valid for MRS')
            mrs_task = MRSTask(mrs_study, context)
            context = mrs_task.process()
        else:
            context.set_failure("Data is not valid for MRS")

        return context
