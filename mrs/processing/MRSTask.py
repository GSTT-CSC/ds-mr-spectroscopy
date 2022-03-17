import os
import pandas as pd
import subprocess
import datetime
from pydicom import dcmread
from typing import Optional

from mrs.tools.tools import calc_mean_xcorr, identify_siemens_mrs_series_type, is_mrs
from mrs.processing.MRSJob import MRSJob
from mrs.reporting.MRSNormalChart import MRSNormalChart, Chart
from mrs.reporting.MRSLayout import MRSLayout

from aide_sdk.utils.file_storage import FileStorage
from aide_sdk.logger.logger import LogManager
from aide_sdk.model.operatorcontext import OperatorContext
from aide_sdk.model.resource import Resource

from mrs.dicom.study import Study
from mrs.dicom.series import Series
from config.config import SETTINGS, APP_DATA_DIR
import mrs.tools.myemail as myemail

log = LogManager.get_logger()


class MRSTask:

    """
    This is the top-level MRS processing class. It is given a DICOM Study object.
    It then groups the series in the Study into the relevant groupings associated with a single MRS processing 'job'.
    It will then make an MRSJob object for each one and call the process method of the MRSJob.
    """
    mrs_app_dir = os.path.join(APP_DATA_DIR)
    qa_dir = os.path.join(mrs_app_dir, 'qa_results')
    qa_db_full_filename = os.path.join(qa_dir, 'qa_res.csv')

    def __init__(self, study: Study, context: Optional[OperatorContext] = None):
        # super(MRSTask, self).__init__(study=study, name='MRS')
        self.study = study
        self.context = context
        self.processed_csv = ''
        self.list_of_mrs_job_input_lists = []

    @property
    def is_qa(self):
        if ('MRS' in self.study.subject_name) and ('QA' in self.study.subject_name):
            return True
        else:
            return False

    @property
    def valid(self) -> bool:
        log.debug('Checking validity of {self.study} for {self} - returns true if Study has an MRS in it.'.format(
            **locals()))
        for series in self.study.series_list:
            for dcm in series.dicom_list:
                if is_mrs(dcm):
                    return True
        else:
            return False

    def process(self):

        if not os.path.exists(MRSTask.mrs_app_dir):  # pragma: no cover
            log.debug('{MRSTask.mrs_app_dir} does not exist. Creating directory now.')
            os.makedirs(MRSTask.mrs_app_dir, exist_ok=True)

        self.build_jobs_list()
        success = False
        for job_series_list in self.list_of_mrs_job_input_lists:

            if len(job_series_list) > 0:

                mrs_job = MRSJob(job_series_list, MRSTask.mrs_app_dir, self.is_qa, MRSTask.qa_dir,
                                 MRSTask.qa_db_full_filename)

                try:

                    mrs_job.mrs_process_job()

                except Exception as e:
                    myemail.nhs_mail(
                        [SETTINGS['mrs']['clinical_email_list']], 'MRS Failure {}'.format(self.study.subject_id),
                        'This MRS Processing job failed to complete and has not been archived to any PACS. The file(s) still '
                        'exists on the dicomserver in an intermediate folder. The process failed with the following '
                        'exception: \n{}'.format(e), [])
                try:
                    context_outptut = self.archive(mrs_job)
                    success = True
                    # log.warning('not archiving here - should be done at operator level')
                except Exception as e:
                    log.exception(e)
                except subprocess.CalledProcessError as e:
                    try:
                        log.critical('Could not archive MRS Job. \nstorescu:\n{}'.format(e.stdout.decode('utf-8')))
                        try:
                            pass
                            myemail.nhs_mail(
                                [SETTINGS['mrs']['clinical_email_list']],
                                'MRS Failure {}'.format(self.study.subject_id),
                                'This MRS Processing job completed but failed to archive to PACS.'
                                'The archive method failed with the following error: '
                                '\n{}'.format(e.stdout.decode('utf-8')),
                                attachments=[])
                        except ConnectionRefusedError:
                            raise
                    except:
                        raise
                try:
                    self.notify(mrs_job)
                except Exception as e:
                    log.warning('Could not send notification of MRS Study {}'.format(e))
                    raise
                if success:
                    log.debug('MRS task complete for subject_id: {}'.format(self.study.subject_id))
                    return context_outptut

    def archive(self, mrs_job):
        """
        Archive dicom files to DICOM store
        Returns
        -------

        """
        log.info("Archiving {mrs_job.water_sup_series}".format(**locals()))

        if self.is_qa:
            log.debug('Study is QA, so do not archive to PACS')
            return

        log.debug(f'Searching for archivable in {mrs_job.job_results_dir}')

        for item in os.listdir(mrs_job.job_results_dir):

            log.debug(f'Item: {item}')

            if 'Tarquin_Output' in item and '.dcm' in item:
                log.debug(f'Tarquin DICOM output: {os.path.join(mrs_job.job_results_dir, item)}')
                mrspath = os.path.join(mrs_job.job_results_dir, item)
                file_manager = FileStorage(self.context)
                outpath = file_manager.save_dicom(item, dcmread(mrspath))
                self.context.add_resource(Resource(format='dicom', content_type='result', file_path=outpath))
        return self.context

    def notify(self, mrs_job):
        """
        Sends out results email

        Returns
        -------
        """

        patient_id = self.study.subject_id

        reports = []

        for item in os.listdir(mrs_job.job_results_dir):
            log.debug('Item: {item}'.format(**locals()))

            # Tarquin produces png files, one for each page of the pdf. Attaching pngs instead of pdf as it can be
            # attached inline of the message.

            if item.endswith('.png'):
                report = os.path.join(mrs_job.job_results_dir, item)
                reports.append(report)

        try:
            log.info('Sending email with PDF attached.')
            myemail.nhs_mail(recipients=[SETTINGS['mrs']['clinical_email_list']],
                             subject='MRS PDF Result: {}'.format(patient_id),
                             message="An MR Spectroscopy has been processed and archived.\n"
                                     "Please review the results attached.\n"
                                     "This email contains patient information, do not forward outside the N3 or "
                                     "GSTT network."
                                     "\n"
                                     "\n"
                                     "\n"
                                     "\n "
                                     "This is an automated email sent by dicomserver: "
                                     "https://bitbucket.org/gsttmri/dicomserver".format(mrs_job.job_results_dir),
                             attachments=reports)
        except Exception as e:
            log.exception(e)
            raise  # because firewall won't let gmail send for some reason, maybe need different port

    def report(self):
        """
        Coded but unused feature - presenting other patient results along with the present study to radiologists.
        The aim is so they can see what is normal and what is abnormal.

        Returns
        -------

        """
        normal_trace = MRSNormalChart().get_trace()

        plot_filename = os.path.join(MRSTask.mrs_app_dir, self.study.series_name)

        mrs_chart = Chart(plot_filename)

        patient_mrs = pd.read_csv(self.processed_csv, header=1)  # header=1 because the first row is not column headers

        x_data = patient_mrs['PPMScale']
        y_data = patient_mrs['Fit']

        patient_trace = mrs_chart.graph.Scatter(x=x_data, y=y_data, line=dict(shape='spline'))

        similarity = calc_mean_xcorr(patient_mrs, [])
        layout = MRSLayout.getLayout(similarity)

        fig = mrs_chart.graph.Figure(data=[normal_trace, patient_trace], layout=layout)

        return mrs_chart.create(figure=fig, filename=plot_filename)

    def build_jobs_list(self):

        mrs_list = []
        # self.list_of_mrs_job_input_lists = [[] for i in range(len(self.study.series_list))]  # List of jobs can only be as long as the number of series is in the Study
        self.list_of_mrs_job_input_lists = []

        # [mrs_list.append(series) for series in self.study.series_list if is_mrs(series)]

        for series in self.study.series_list:

            tmp = []
            for dcm in series.dicom_list:
                if is_mrs(dcm):
                    tmp.append(dcm)

            if tmp:
                mrs_list.append(Series(dicom_list=tmp))

        if self.is_qa is True:
            # If this is a QA study, usually only one 'job' - i.e. if Philips, single DICOM; if Siemens, two DICOMs (acq and water ref)
            # BUT - if there ARE multiple jobs in the study - collect them serially
            siemens_water_sup_list = []
            siemens_water_ref_list = []

            for series in mrs_list:
                if series.manufacturer == 'Philips Medical Systems':
                    self.list_of_mrs_job_input_lists.append([series])  # Note the square brackets - that's because each elements of the jobs list is a list of series for each job

                elif series.manufacturer.lower() == 'siemens':

                    series_type = identify_siemens_mrs_series_type(series)
                    if 'water_reference' in series_type:
                        siemens_water_ref_list.append(series)
                    elif 'water_suppressed' in series_type:
                        siemens_water_sup_list.append(series)
                    else:
                        log.debug(
                            'Series {series} is not water_reference or water_suppressed - not adding to MRSJob list')

            if series.manufacturer.lower() == 'siemens':

                N_min = min(len(siemens_water_ref_list), len(siemens_water_sup_list))

                [self.list_of_mrs_job_input_lists.append([siemens_water_ref_list[i], siemens_water_sup_list[i]]) for
                 i in range(0, N_min)]

                if len(siemens_water_ref_list) != len(siemens_water_sup_list):
                    log.warning(
                        'Number of water references in series does not equal number of water suppressed scans')

        elif self.is_qa is False:
            # New version of Siemens Patient data job-sorting code
            datetimes = []
            for series in mrs_list:
                if ('_ref' in series.dicom_list[0].SeriesDescription) and (series.manufacturer.lower() == 'siemens'):
                    self.list_of_mrs_job_input_lists.append([series])  # Square brackets here to make list of containing list for each job
                    datetimes.append(datetime.datetime.strptime(series.dicom_list[0].AcquisitionDateTime, '%Y%m%d%H%M%S.%f'))

            # Now filter other series
            for series_tmp in mrs_list:
                if '_ref' not in series_tmp.dicom_list[0].SeriesDescription:
                    datetime_candidate = datetime.datetime.strptime(series_tmp.dicom_list[0].AcquisitionDateTime,'%Y%m%d%H%M%S.%f')
                    if not datetimes:
                        # List is empty, so add candidate as a job
                        datetimes.append(datetime_candidate)
                        self.list_of_mrs_job_input_lists.append([series_tmp])
                    else:
                        dt_diff = [abs((x - datetime_candidate).total_seconds()) for x in datetimes]

                        min_dt_diff = min(dt_diff)
                        min_dt_diff_index = dt_diff.index(min(dt_diff))

                        if min_dt_diff <= int(SETTINGS['mrs']['job_ref_acq_time_diff_thresh']):
                            self.list_of_mrs_job_input_lists[min_dt_diff_index].append(series_tmp)
                        elif min_dt_diff > int(SETTINGS['mrs']['job_ref_acq_time_diff_thresh']):
                            if series_tmp.manufacturer.lower() == 'siemens':
                                log.info('Could not assign series {series_tmp} to a job')
                            elif series_tmp.manufacturer == 'Philips Medical Systems':
                                self.list_of_mrs_job_input_lists.append([series_tmp])
                                datetimes.append(datetime_candidate)

        return
