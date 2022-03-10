import unittest
import os
import pytest
import shutil

from mrs.tools.exceptions import InvalidInputData
from mrs.dicom.study import Study
from mrs.dicom.series import Series
from mrs.dicom.dicom import Dicom
from config.config import APP_DATA_DIR
from mrs.processing.MRSTask import MRSTask
from mrs.processing.MRSJob import MRSJob

import logging

# MRS_DATA_DIR = os.path.join(TEST_DATA_DIR, 'mrs')
MRS_DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'mrs')
os.makedirs(MRS_DATA_DIR, exist_ok=True)

logging.basicConfig(filename='tests_log.log', encoding='utf-8', level=logging.DEBUG)
log = logging.getLogger(__name__)


class TestPhilipsMRSStudy(unittest.TestCase):

    def setUp(self):
        self.philips_patient_mrs_2j1s = Study(study_dir=os.path.join(MRS_DATA_DIR, 'philips/two_jobs_one_study'))
        self.philips_patient_mrs_process_task_2j1s = MRSTask(study=self.philips_patient_mrs_2j1s)

        self.philips_patient_mrs_dynamics = Study(
            dicom_list=[Dicom(os.path.join(MRS_DATA_DIR, 'philips/dynamics/dynamics.dcm'))])
        self.philips_patient_mrs_process_task_dynamics = MRSTask(study=self.philips_patient_mrs_dynamics)

        self.philips_patient_mrs = Study(study_dir=os.path.join(MRS_DATA_DIR, 'philips/Mouse_Anony/mri_head_study'))
        self.philips_patient_mrs_process_task = MRSTask(study=self.philips_patient_mrs)

        self.philips_QA_mrs = Study(dicom_list=[Dicom(os.path.join(MRS_DATA_DIR,
                                                                   'philips/ECH_QA/MRS_ECH_DTI_QA_20180717_MRS_shortTE_LN_Series_401_MRS_DICOM_Data.dcm'))])
        self.philips_QA_mrs_process_task = MRSTask(study=self.philips_QA_mrs)

        raw_and_mrs = os.path.join(MRS_DATA_DIR, 'philips', 'raw_and_mrs')
        raw = Dicom(f=os.path.join(raw_and_mrs, 'RAW.dcm'))
        mrs = Dicom(f=os.path.join(raw_and_mrs, 'MRs.dcm'))

        # Collect into list and construct Study object
        dcm_list = [raw, mrs]
        mrs_dti_qa = Study(dicom_list=dcm_list)

        # Create processing object
        self.qa_process = MRSTask(study=mrs_dti_qa)

    def testDynamics(self):
        log.info('TestDynamics')

        mrs_job = build_job(self.philips_patient_mrs_process_task_dynamics)
        assert mrs_job.mrs_process_job()
        log.debug(mrs_job.job_results_dir)
        assert os.path.exists(os.path.join(
            mrs_job.job_results_dir,
            'test_20210303_medv_PRESS_55_tr1500_Tarquin_Output-0.png'))
        assert os.path.exists(os.path.join(
            mrs_job.job_results_dir,
            'test_20210303_medv_PRESS_55_tr1500_Tarquin_Output-1.png'))
        print(mrs_job.job_results_dir)
        return True

    def testTwoJobsOneStudy(self):
        res_dir = os.path.join(APP_DATA_DIR, '1234A', '20190205')
        try:
            shutil.rmtree(res_dir)
        except:
            pass
        self.philips_patient_mrs_process_task_2j1s.process()
        N_res = len([i for i in os.listdir(res_dir) if os.path.isdir(os.path.join(res_dir, i))])
        assert N_res == 2

    def testRawAndMRSStudy(self):
        res_dir = os.path.join(APP_DATA_DIR, 'MRS_DTI_QA', '20180404')
        try:
            shutil.rmtree(res_dir)
        except:
            pass
        self.qa_process.process()
        N_res = len([i for i in os.listdir(res_dir) if os.path.isdir(os.path.join(res_dir, i))])
        assert N_res == 1

    def testValidPhilipsMRS(self):
        log.info('testValidPhilipsMRS')
        assert self.philips_patient_mrs.valid is True
        assert self.philips_QA_mrs.valid is True

    def testValidRawAndMRS(self):
        log.info('testValidRawAndMRS')

        assert self.qa_process.valid is True

    def testProcessSinglePhilipsMRSDicom(self):
        log.info('testProcessSinglePhilipsMRSDicom')
        mrs_job = build_job(self.philips_patient_mrs_process_task)
        assert mrs_job.mrs_process_job()
        assert os.path.exists(os.path.join(
            mrs_job.job_results_dir,
            '1234567A_20160531_MRS_shortTE_LN_BG__Tarquin_Output-1.png'))

    def testProcessSinglePhilipsMRSQADicom(self):
        log.info('testProcessSinglePhilipsMRSQADicom')
        mrs_job = build_job(self.philips_QA_mrs_process_task)
        assert mrs_job.mrs_process_job()
        assert os.path.exists(os.path.join(
            mrs_job.job_results_dir,
            'MRS_ECH_DTI_QA_20180717_MRS_shortTE_LN_Tarquin_Output-1.png'))

    def testMissingPulseSequenceTag(self):
        log.info('testMissingPulseSequenceTag')

        del self.philips_patient_mrs_process_task.study.series_list[0].dicom_list[0].PulseSequenceName

        with pytest.raises(InvalidInputData):
            _ = self.philips_patient_mrs_process_task.valid

    @pytest.mark.skip
    def testReport(self):
        log.info('testReport')
        assert self.philips_patient_mrs_process_task.report() == "file://" + os.path.join(
            self.philips_patient_mrs_process_task.result_directory, 'MRS_shortTE_LN__BG__chart.html')


class TestSiemensMRSStudy(unittest.TestCase):

    def setUp(self):
        log.info('Setting up Siemens MRS Test studies and tasks')

        # Non-MRS Data
        self.siemens_nonmrs_study = Study(series_list=[Series(series_dir=os.path.join(MRS_DATA_DIR, 'siemens/nonmrs'))])
        self.siemens_nonmrs_task = MRSTask(study=self.siemens_nonmrs_study)

        # MRS Data - UNENHANCED DICOM format - don't expect this to work anymore
        # self.siemens_mrs_qa_old = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/qa'))
        # self.siemens_mrs_qa_old_task = MRSTask(study=self.siemens_mrs_qa_old)

        # MRS mMR QA Data - syngo.via exported (enhanced) - VB20p
        self.siemens_mrs_qa_1 = Study(
            study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112112/pre_upgrade_sv_export_enhanced'))
        self.siemens_mrs_qa_1_task = MRSTask(study=self.siemens_mrs_qa_1)

        # MRS mMR QA Data - syngo.via exported (intra-operability) - VB20p
        self.siemens_mrs_qa_2 = Study(
            study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112112/pre_upgrade_sv_export_interoperability'))
        self.siemens_mrs_qa_2_task = MRSTask(study=self.siemens_mrs_qa_2)

        # MRS mMR QA Data - syngo.via exported (enhanced) - VE11p
        self.siemens_mrs_qa_3 = Study(
            study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112113/post_upgrade_sv_export_enhanced'))
        self.siemens_mrs_qa_3_task = MRSTask(study=self.siemens_mrs_qa_3)

        # MRS mMR QA Data - syngo.via exported (intra-operability) - VE11p
        self.siemens_mrs_qa_4 = Study(
            study_dir=os.path.join(MRS_DATA_DIR, 'siemens/18112113/post_upgrade_sv_export_interoperability'))
        self.siemens_mrs_qa_4_task = MRSTask(study=self.siemens_mrs_qa_4)

        # Anon Patient Data from Syngo.via
        self.siemens_mrs_patPO = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens/pat_data_sv/PO'))
        self.siemens_mrs_patPO_task = MRSTask(study=self.siemens_mrs_patPO)

        # Vida test data - entire dataset
        self.vida_svs_se_all = Study(study_dir=os.path.join(MRS_DATA_DIR, 'siemens', 'xa20_test_data', 'all'))

    def testValidSiemensQAMRS(self):
        log.info('testValidSiemensQAMRS')
        assert self.siemens_nonmrs_task.is_qa is False
        # assert self.siemens_mrs_qa_old_task.is_qa is True
        assert self.siemens_mrs_qa_1_task.is_qa is True
        assert self.siemens_mrs_qa_2_task.is_qa is True
        assert self.siemens_mrs_qa_3_task.is_qa is True
        assert self.siemens_mrs_qa_4_task.is_qa is True
        assert self.siemens_mrs_patPO_task.is_qa is False

    def testMRSProcessSiemensQAMRS(self):
        log.info("testMRSProcessSiemensQAMRS")

        mrs_job = build_job(self.siemens_mrs_qa_2_task)
        assert mrs_job.mrs_process_job()
        mrs_job = build_job(self.siemens_mrs_qa_4_task)
        assert mrs_job.mrs_process_job()
        mrs_job = build_job(self.siemens_mrs_qa_1_task)
        assert mrs_job.mrs_process_job()
        mrs_job = build_job(self.siemens_mrs_qa_3_task)
        assert mrs_job.mrs_process_job()

    def testValidSiemensNonMRS(self):
        log.info("testValidSiemensNonMRS")
        assert self.siemens_nonmrs_task.valid is False

    def testMRSProcessSiemensMRS(self):
        log.info('testMRSProcessSiemensMRS')
        mrs_job = build_job(self.siemens_mrs_patPO_task)
        assert mrs_job.mrs_process_job()

    def testSiemensMRSXA20Pipeline(self):
        log.info('testSiemensMRSXA20Pipeline')

        # Delete previous results directory
        tmp_path = os.path.join(APP_DATA_DIR, 'mrs', 'GSTTQA')
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)

        # Test MRSTask is valid
        self.vida_svs_se_all_task = MRSTask(study=self.vida_svs_se_all)
        assert self.vida_svs_se_all_task.valid is True

        # Run MRSTask jobs
        self.vida_svs_se_all_task.process()
        # Check files exist
        assert os.path.exists(os.path.join(APP_DATA_DIR, 'GSTTQA', '20210218', 'MRS_te30_15x25x15_saveall_ECC',
                                           'GSTTQA_20210218_MRS_te30_15x25x15_saveall_ECC__Tarquin_Output_Extended_Plot.dcm'))
        assert os.path.exists(os.path.join(APP_DATA_DIR, 'GSTTQA', '20210218', 'MRS_te144_15x25x15_saveall_ECC',
                                           'GSTTQA_20210218_MRS_te144_15x25x15_saveall_ECC__Tarquin_Output_Extended_Plot.dcm'))
        assert os.path.exists(os.path.join(APP_DATA_DIR, 'GSTTQA', '20210218', 'MRS_te288_15x25x15_saveall_ECC',
                                           'GSTTQA_20210218_MRS_te288_15x25x15_saveall_ECC__Tarquin_Output_Extended_Plot.dcm'))


if __name__ == '__main__':
    unittest.main()


def build_job(task_in):
    task_in.build_jobs_list()
    mrs_job = MRSJob(task_in.list_of_mrs_job_input_lists[0], task_in.mrs_app_dir, task_in.is_qa, task_in.qa_dir,
                     task_in.qa_db_full_filename)
    return mrs_job
