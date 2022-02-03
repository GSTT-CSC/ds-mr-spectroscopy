import unittest
import os
import pytest
import shutil
import glob


from dicomserver.logger import log
from dicomserver_tests import TEST_DATA_DIR
from dicomserver.exceptions import InvalidInputData
from dicomserver.processing.mrs import MRSTask, MRSJob
from dicomserver.dicom import Series, Study, Dicom
from dicomserver.config import SETTINGS

MRS_DATA_DIR = os.path.join(TEST_DATA_DIR, 'mrs')
os.makedirs(MRS_DATA_DIR, exist_ok=True)


class TestPhilipsMRSStudy_0_10_7(unittest.TestCase):

    def setUp(self):
        self.philips_patient_mrs_2j1s = Study(study_dir=os.path.join(MRS_DATA_DIR, 'philips/two_jobs_one_study'))
        self.philips_patient_mrs_process_task_2j1s = MRSTask(study=self.philips_patient_mrs_2j1s)

        self.philips_patient_mrs = Study(study_dir=os.path.join(MRS_DATA_DIR, 'philips/Mouse_Anony/mri_head_study'))
        self.philips_patient_mrs_process_task = MRSTask(study=self.philips_patient_mrs)

        self.philips_QA_mrs = Study(dicom_list=[Dicom(os.path.join(MRS_DATA_DIR, 'philips/ECH_QA/MRS_ECH_DTI_QA_20180717_MRS_shortTE_LN_Series_401_MRS_DICOM_Data.dcm'))])
        self.philips_QA_mrs_process_task = MRSTask(study=self.philips_QA_mrs)

        raw_and_mrs = os.path.join(MRS_DATA_DIR, 'philips', 'raw_and_mrs')
        raw = Dicom(f=os.path.join(raw_and_mrs, 'RAW.dcm'))
        mrs = Dicom(f=os.path.join(raw_and_mrs, 'MRs.dcm'))

        # Collect into list and construct Study object
        dcm_list = [raw, mrs]
        mrs_dti_qa = Study(dicom_list=dcm_list)

        # Create processing object
        self.qa_process = MRSTask(study=mrs_dti_qa)

    def testTwoJobsOneStudy_0_10_7(self):
        res_dir = os.path.join(SETTINGS['dicomserver']['data_dir'], 'mrs', '1234A', '20190205')
        try:
            shutil.rmtree(res_dir)
        except:
            pass
        self.philips_patient_mrs_process_task_2j1s.process()
        N_res = len([i for i in os.listdir(res_dir) if os.path.isdir(os.path.join(res_dir, i))])
        assert N_res == 2

    def testRawAndMRSStudy_0_10_7(self):
        res_dir = os.path.join(SETTINGS['dicomserver']['data_dir'], 'mrs', 'MRS_DTI_QA', '20180404')
        try:
            shutil.rmtree(res_dir)
        except:
            pass
        self.qa_process.process()
        N_res = len([i for i in os.listdir(res_dir) if os.path.isdir(os.path.join(res_dir, i))])
        assert N_res == 1

    def testValidPhilipsMRS_0_10_7(self):
        log.info('testValidPhilipsMRS')
        assert self.philips_patient_mrs.valid is True
        assert self.philips_QA_mrs.valid is True

    def testValidRawAndMRS_0_10_7(self):
        log.info('testValidRawAndMRS')

        assert self.qa_process.valid is True

    def testProcessSinglePhilipsMRSDicom_0_10_7(self):
        log.info('testProcessSinglePhilipsMRSDicom')
        mrs_job = build_job(self.philips_patient_mrs_process_task)
        assert mrs_job.mrs_process_job()
        assert os.path.exists(os.path.join(
        mrs_job.job_results_dir,
           '1234567A_20160531_MRS_shortTE_LN_BG__Tarquin_Output-1.png'))

    def testProcessSinglePhilipsMRSQADicom_0_10_7(self):
        log.info('testProcessSinglePhilipsMRSQADicom')
        mrs_job = build_job(self.philips_QA_mrs_process_task)
        assert mrs_job.mrs_process_job()
        assert os.path.exists(os.path.join(
            mrs_job.job_results_dir,
            'MRS_ECH_DTI_QA_20180717_MRS_shortTE_LN_Tarquin_Output-1.png'))



    def testMissingPulseSequenceTag_0_10_7(self):
        log.info('testMissingPulseSequenceTag')

        del self.philips_patient_mrs_process_task._study.series_list[0].dicom_list[0].PulseSequenceName

        with pytest.raises(InvalidInputData):
            _ = self.philips_patient_mrs_process_task.valid


    @pytest.mark.skip
    def testReport(self):
        log.info('testReport')
        assert self.philips_patient_mrs_process_task.report() == "file://" + os.path.join(self.philips_patient_mrs_process_task.result_directory, 'MRS_shortTE_LN__BG__chart.html')


class TestSiemensMRSStudy_0_10_7(unittest.TestCase):

    def setUp(self):
        log.info('Setting up Siemens MRS Test studies and tasks')

        # Non-MRS Data
        self.siemens_nonmrs_study = Study(series_list=[Series(series_dir=os.path.join(MRS_DATA_DIR, 'siemens/nonmrs'))])
        self.siemens_nonmrs_task = MRSTask(study=self.siemens_nonmrs_study)

        # MRS Data - UNENHANCED DICOM format - don't expect this to work anymore
        # self.siemens_mrs_qa_old = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/qa'))
        # self.siemens_mrs_qa_old_task = MRSTask(study=self.siemens_mrs_qa_old)

        # MRS mMR QA Data - syngo.via exported (enhanced) - VB20p
        self.siemens_mrs_qa_1 = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112112/pre_upgrade_sv_export_enhanced'))
        self.siemens_mrs_qa_1_task = MRSTask(study=self.siemens_mrs_qa_1)

        # MRS mMR QA Data - syngo.via exported (intra-operability) - VB20p
        self.siemens_mrs_qa_2 = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112112/pre_upgrade_sv_export_interoperability'))
        self.siemens_mrs_qa_2_task = MRSTask(study=self.siemens_mrs_qa_2)

        # MRS mMR QA Data - syngo.via exported (enhanced) - VE11p
        self.siemens_mrs_qa_3 = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112113/post_upgrade_sv_export_enhanced'))
        self.siemens_mrs_qa_3_task = MRSTask(study=self.siemens_mrs_qa_3)

        # MRS mMR QA Data - syngo.via exported (intra-operability) - VE11p
        self.siemens_mrs_qa_4 = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112113/post_upgrade_sv_export_interoperability'))
        self.siemens_mrs_qa_4_task = MRSTask(study=self.siemens_mrs_qa_4)

        # Anon Patient Data from Syngo.via
        self.siemens_mrs_patPO = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/pat_data_sv/PO'))
        self.siemens_mrs_patPO_task = MRSTask(study=self.siemens_mrs_patPO)

    def testValidSiemensQAMRS_0_10_7(self):
        log.info('testValidSiemensQAMRS')
        assert self.siemens_nonmrs_task.is_qa is False
        # assert self.siemens_mrs_qa_old_task.is_qa is True
        assert self.siemens_mrs_qa_1_task.is_qa is True
        assert self.siemens_mrs_qa_2_task.is_qa is True
        assert self.siemens_mrs_qa_3_task.is_qa is True
        assert self.siemens_mrs_qa_4_task.is_qa is True
        assert self.siemens_mrs_patPO_task.is_qa is False

    def testMRSProcessSiemensQAMRS_0_10_7(self):
        log.info("testMRSProcessSiemensQAMRS")

        mrs_job = build_job(self.siemens_mrs_qa_2_task)
        assert mrs_job.mrs_process_job()
        mrs_job = build_job(self.siemens_mrs_qa_4_task)
        assert mrs_job.mrs_process_job()
        mrs_job = build_job(self.siemens_mrs_qa_1_task)
        assert mrs_job.mrs_process_job()
        mrs_job = build_job(self.siemens_mrs_qa_3_task)
        assert mrs_job.mrs_process_job()

    def testValidSiemensNonMRS_0_10_7(self):
        log.info("testValidSiemensNonMRS")
        assert self.siemens_nonmrs_task.valid is False

    def testMRSProcessSiemensMRS_0_10_7(self):
        log.info('testMRSProcessSiemensMRS')
        mrs_job = build_job(self.siemens_mrs_patPO_task)
        assert mrs_job.mrs_process_job()


if __name__ == '__main__':
    unittest.main()


def build_job(task_in):
    task_in.build_jobs_list()
    mrs_job = MRSJob(task_in.list_of_mrs_job_input_lists[0], task_in.mrs_app_dir, task_in.is_qa, task_in.qa_dir, task_in.qa_db_full_filename)
    return mrs_job
