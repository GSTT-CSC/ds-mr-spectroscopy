import numpy as np
import re
import os
import shutil
import suspect
import subprocess
import glob
import csv
import datetime
import pydicom as pyd
import copy
import PyPDF2

from config.config import SETTINGS
from mrs import VERSION
from PIL import Image
import mrs.tools.myemail as myemail
from mrs.dicom.series import Series
from mrs.tools.tools import get_te_ms, get_voxel_size, identify_siemens_mrs_series_type, fwhm, make_qa_plots, analysis, get_tf_mhz
from aide_sdk.logger.logger import LogManager


log = LogManager.get_logger()


class MRSJob:
    """
    - This is a class which takes a list of DICOM series which constitute a single 'MRS Job'.
    - For example, one water suppressed and one water unsuppressed DICOM is needed for some MRS processing jobs
    """

    def __init__(self, series_list, mrs_app_dir, is_qa, qa_dir, qa_db_full_filename):
        self.mrs_app_dir = mrs_app_dir
        self.is_qa = is_qa
        self.qa_dir = qa_dir
        self.qa_db_full_filename = qa_db_full_filename
        self.series_list = series_list
        self.tarquin_log_filename = ''
        self.clean_job_name = ''
        self.output_filename_root = ''
        self.job_results_dir = ''
        self.water_sup_series: Series = []
        self.water_ref_series: Series = []
        self.png_filename = ''

    def mrs_process_job(self) -> bool:
        """
        This method processes MR Spectroscopy data. It will utilise Tarquin for Philips data (patient and QA) and Siemens patient data, and an in-house processing algorithm for Siemens QA data from the mMR

        :return:
            report: True is processing is successful, else an exception
        """

        log.info('Processing MR Spectroscopy Job...')

        # Check job is valid
        if self.series_list[0].manufacturer == 'Philips Medical Systems':
            if len(self.series_list) != 1:
                raise Exception(
                    'Philips MRSJob, but number of series in series_list is not one. Therefore not possible to process')
        elif (self.series_list[0].manufacturer.lower() == 'siemens'):
            if (len(self.series_list) > 3) or (len(self.series_list) == 0):
                raise Exception(
                    'Siemens MRSJob, but number of series in series_list is bigger than three or zero. Therefore not possible to process.')

        # Sort through series list to figure out the water suppressed and any water reference scan
        if self.series_list[0].manufacturer == 'Philips Medical Systems':
            self.water_sup_series = self.series_list[0]
        elif (self.series_list[0].manufacturer.lower() == 'siemens'):
            self.water_sup_series, self.water_ref_series = self.sort_out_siemens_mrs_data()

        # Make useful strings
        self.clean_job_name = re.sub("[^0-9a-zA-Z]+", '_', self.water_sup_series.series_name)
        self.output_filename_root = self.water_sup_series.subject_id + '_' + self.water_sup_series.study_date + '_' + self.clean_job_name + '_'

        # Results folder specifically for this job
        self.job_results_dir = os.path.join(self.mrs_app_dir, self.water_sup_series.subject_id,
                                            self.water_sup_series.study_date, self.clean_job_name)
        log.debug('Making job directory: {self.job_results_dir}'.format(**locals()))
        os.makedirs(self.job_results_dir, exist_ok=True)

        log.debug('Archiving raw series to results folder')
        shutil.copyfile(self.water_sup_series.dicom_list[0].filename,
                        os.path.join(self.job_results_dir, self.output_filename_root + 'MRS_DICOM_data.dcm'))
        if bool(self.water_ref_series) is True:
            shutil.copyfile(self.water_ref_series.dicom_list[0].filename,
                            os.path.join(self.job_results_dir, self.output_filename_root + 'MRS_DICOM_data_ref.dcm'))

        if (self.water_sup_series.dicom_list[0].Manufacturer.lower() == 'siemens') and (self.is_qa is True):

            log.debug('Performing Siemens MRS QA processing')

            res = self.process_siemens_qa_data()

            try:
                log.debug('Archiving Siemens QA results to csv file')
                self.archive_siemens_qa(res)
            except:
                raise Exception("Could not archive data")

            try:
                log.debug('Making plots and sending email')
                self.report_siemens_qa()
                return True
            except:
                log.debug('Reporting failed')
                raise Exception("Could not report data")

        else:
            if self.series_list[0].manufacturer == 'Philips Medical Systems':
                series_name = self.series_list[0].series_name
                series_uid = self.series_list[0].series_uid
                log.debug(f'Reading Philips [{series_name}/{series_uid}] .dcm with suspect')
                raw_data = suspect.io.load_dicom(self.water_sup_series.dicom_list[0].filename)
                dynamics = raw_data.shape[0]
                ws_dynamics = dynamics // 2  # This matches all current Philips test data
                log.debug('Separating Philips water reference from WS data and averaging transients')
                mean_raw_data = np.mean(raw_data[0:ws_dynamics, :], axis=0)
                mean_water_ref_data = np.mean(raw_data[ws_dynamics:, :], axis=0)
                # Overwrite suspect default TE, no other method available
                raw_data._te = float(get_te_ms(self.water_sup_series))
                mean_raw_data._te = float(get_te_ms(self.water_sup_series))
                mean_water_ref_data._te = float(get_te_ms(self.water_sup_series))
                log.debug(f'TE of processed spectrum is {mean_raw_data._te} ms')
                log.debug(
                    'doing spectral registration in the frequency domain using suspect for water suppressed Philips data')
                tf = get_tf_mhz(self.water_sup_series)
                fc_data = suspect.processing.frequency_correction.correct_frequency_and_phase(raw_data[0:ws_dynamics],
                                                                                              raw_data[0],
                                                                                              method='rats',
                                                                                              frequency_range=(
                                                                                              1.7 * tf, 5.5 * tf)
                                                                                              )
                final_fc_data = np.mean(fc_data, axis=0)
                log.debug(
                    'doing spectral registration in the frequency domain using suspect for water unsuppressed Philips data')
                fc_data_ref = suspect.processing.frequency_correction.correct_frequency_and_phase(
                    raw_data[ws_dynamics:],
                    raw_data[ws_dynamics],
                    method='rats',
                    frequency_range=None
                    )

                final_fc_data_ref = np.mean(fc_data_ref, axis=0)

                log.debug('Saving TARQUIN dpt files')
                suspect.io.tarquin.save_dpt(os.path.join(self.job_results_dir, self.output_filename_root + 'fc.dpt'),
                                            final_fc_data)
                suspect.io.tarquin.save_dpt(
                    os.path.join(self.job_results_dir, self.output_filename_root + 'fc_ref.dpt'), final_fc_data_ref)
                suspect.io.tarquin.save_dpt(os.path.join(self.job_results_dir, self.output_filename_root + 'avg.dpt'),
                                            mean_raw_data)
                suspect.io.tarquin.save_dpt(
                    os.path.join(self.job_results_dir, self.output_filename_root + 'avg_ref.dpt'), mean_water_ref_data)

            log.debug('Performing Tarquin processing')

            command = self.build_tarquin_command()

            log.debug('Writing tarquin command line to a text file so it is easy to rerun on a later date')
            with open(os.path.join(self.job_results_dir, self.output_filename_root + 'tarquin_command.txt'),
                      "w") as text_file:
                text_file.write(" ".join(command))

            log.debug('Tarquin command to be executed: {command}'.format(**locals()))
            try:
                result = subprocess.run(command, shell=False, stdout=subprocess.PIPE, cwd=self.job_results_dir)
                result = subprocess.run(['tee', self.tarquin_log_filename], input=result.stdout)
            except Exception as e:
                log.debug('Execution of Tarquin command failed')
                raise e

            log.debug('Re-running gnuplot')
            # Read in the file
            with open(os.path.join(self.job_results_dir, 'gnuplot.txt'), 'r') as file:
                filedata = file.read()

            # Replace the target string
            filedata = filedata.replace('set timestamp top',
                                        'set timestamp top; set label "CAUTION: Tarquin was used to analyse this MRS data. Take care when comparing with previous LCModel results" at screen(0.5),graph(1.1) textcolor "red" center font "Courier,16" ; set label "CAUTION: Tarquin was used to analyse this MRS data. Take care when comparing with previous LCModel results" at screen(0.5),graph(-0.1) textcolor "red" center font "Courier,16" ')

            # Write the file out again
            with open(os.path.join(self.job_results_dir, 'gnuplot.txt'), 'w') as file:
                file.write(filedata)

            cwd = os.getcwd()
            os.chdir(self.job_results_dir)
            subprocess.run(
                'export DYLD_LIBRARY_PATH=""; ' + SETTINGS['mrs']['gnuplot'] + ' "' + os.path.join(self.job_results_dir,
                                                                                                   'gnuplot.txt') + '"',
                shell=True)
            os.chdir(cwd)

            log.debug('Rename Tarquin output files')
            f_list = os.listdir(self.job_results_dir)
            for f in f_list:
                if str.startswith(f, self.output_filename_root) is False:
                    os.rename(os.path.join(self.job_results_dir, f),
                              os.path.join(self.job_results_dir, self.output_filename_root + f))

            log.debug('Converting PDF to PNG format')
            self.png_filename = self.output_filename_root + 'Tarquin_Output'
            try:
                cwd = os.getcwd()
                os.chdir(self.job_results_dir)
                subprocess.run(['convert', '-density', '300',
                                os.path.join(self.job_results_dir, self.output_filename_root + 'Tarquin_Output.pdf'),
                                os.path.join(self.job_results_dir, self.png_filename + '.png')], check=True)
                os.chdir(cwd)
            except:
                raise

            log.debug('Converting PNG to DICOM')
            self.create_mrs_dicom()

        return True

    def build_tarquin_command(self):

        log.debug('Running build_tarquin_command')

        vox = get_voxel_size(self.water_sup_series)
        vox_num = [float(i) for i in vox]
        volume_ml = str(np.prod(vox_num) / 1000)
        log.debug('Voxel size = {vox} and volumes from DICOM'.format(**locals()))

        te_ms = get_te_ms(self.water_sup_series)
        log.debug('TE = {te_ms} from DICOM'.format(**locals()))

        # Build output file names
        tarquin_output_pdf_filename = os.path.join(self.job_results_dir,
                                                   self.output_filename_root + 'Tarquin_Output.pdf')
        tarquin_output_csv_filename = '"' + os.path.join(self.job_results_dir,
                                                         self.output_filename_root + 'Tarquin_Output.csv"')
        self.tarquin_log_filename = os.path.join(self.job_results_dir, self.output_filename_root + 'Tarquin_Log.txt')

        # Build output PDF title
        tarquin_output_pdf_title = 'PatientID:' + self.water_sup_series.subject_id + \
                                   ' Date: ' + self.water_sup_series.study_date + ' \\n' + \
                                   self.clean_job_name + \
                                   ', TE = ' + te_ms + \
                                   ' ms, voxel size = ' + vox[0] + 'x' + vox[1] + 'x' + vox[2] + \
                                   ' mm, volume = ' + volume_ml + ' ml'

        tarquin_output_pdf_title = re.sub('_', '-', tarquin_output_pdf_title)

        # Now start building string for Tarquin command
        input_string = ''
        if self.water_sup_series.dicom_list[0].Manufacturer == 'Philips Medical Systems':
            input_string = ['--input'] + [os.path.join(self.job_results_dir, self.output_filename_root + 'fc.dpt')] \
                           + ['--input_w'] + [
                               os.path.join(self.job_results_dir, self.output_filename_root + 'fc_ref.dpt')] \
                           + ['--format'] + ['dpt'] + ['--max_dref'] + ['0.5']
        else:
            input_string = ['--input'] + [self.water_sup_series.dicom_list[0].filename]

        output_pdf_string = ['--output_pdf'] + [tarquin_output_pdf_filename]
        output_pdf_title_string = ['--title'] + [tarquin_output_pdf_title]
        output_fit_string = ['--output_fit'] + [tarquin_output_csv_filename]
        gnuplot_string = ['--gnuplot'] + [SETTINGS['mrs']['gnuplot']] + ['--stack_pdf'] + ['true']

        log.debug('Building Tarquin parameter string')
        tarquin_param_string = self.build_tarquin_param_string()

        if self.is_qa is False:
            if self.water_sup_series.dicom_list[0].Manufacturer.lower() == 'siemens':
                input_string = input_string + ['--input_w'] + [self.water_ref_series.dicom_list[0].filename]
        else:
            if self.water_sup_series.dicom_list[0].Manufacturer.lower() == 'siemens':
                log.debug('Should not have got to this point, as not using tarquin for Siemens QA - raise error')
                raise Exception('Should not have got to this point')

        command = [
                      'tarquin'] + input_string + tarquin_param_string + output_pdf_string + output_pdf_title_string + output_fit_string + gnuplot_string

        return command

    def sort_out_siemens_mrs_data(self):
        """

        Returns
        -------
        water_sup_series: dicomserver.dicom.Series
            The series in self.series_list which is the water suppressed MRS

        water_ref_series: dicomserver.dicom.Series
            The series in self.series_list which is the water reference MRS
        """
        water_sup_series = []
        water_ref_series = []
        # This code distinguishes between water UN-suppressed and water suppressed file
        for x in self.series_list:
            if identify_siemens_mrs_series_type(x) == 'water_reference':
                water_ref_series = x
            elif (identify_siemens_mrs_series_type(x) == 'water_suppressed_ECC') or (
                    identify_siemens_mrs_series_type(x) == 'water_suppressed'):
                water_sup_series = x
        if water_sup_series == []:
            return Exception('Could not find water suppressed scan in Siemens MRS JOB')

        return water_sup_series, water_ref_series

    def build_tarquin_param_string(self):

        log.debug('Building Tarquin parameter string from mrs.cfg SETTINGS')

        param_str = []
        settings_field = ''

        if self.water_sup_series.dicom_list[0].Manufacturer.lower() == 'siemens':
            if self.is_qa is True:
                settings_field = 'siemens_qa_tarquin_params'
            if self.is_qa is False:
                return param_str
        elif self.water_sup_series.dicom_list[0].Manufacturer == 'Philips Medical Systems':
            if self.is_qa is True:
                settings_field = 'philips_qa_tarquin_params'
            if self.is_qa is False:
                return param_str
        else:
            log.debug('Unknown manufacturer')
            return param_str

        for name, value in SETTINGS.items(settings_field):
            param_str = param_str + ['--' + str(name)] + [str(value)]

        return param_str

    def create_mrs_dicom(self):

        # ALTERNATIVE TO THIS FUNCTION
        # pdf2dcm +se REFERENCE_DCM.dcm INPUT_PDF.pdf OUTPUT_DICOM.dcm

        log.debug('Running create_mrs_dicom function')

        dcm = self.water_sup_series.dicom_list[0]

        # Populate required values for file meta information
        log.debug("Setting file meta information...")
        file_meta = pyd.Dataset()
        unique_uid = pyd.uid.generate_uid()
        elements_to_define_meta = {'FileMetaInformationGroupLength': 210,
                                   'MediaStorageSOPClassUID': '1.2.840.10008.5.1.4.1.1.7',
                                   'ImplementationVersionName': 'dicomserver ' + VERSION,
                                   'MediaStorageSOPInstanceUID': unique_uid,
                                   }
        elements_to_transfer_meta = {'ImplementationClassUID': 'ImplementationClassUID',
                                     'FileMetaInformationVersion': 'FileMetaInformationVersion',
                                     'TransferSyntaxUID': 'TransferSyntaxUID',
                                     }

        log.debug('Add the data elements to the metadata')
        for k, v in elements_to_define_meta.items():
            setattr(file_meta, k, v)

        for k, v in elements_to_transfer_meta.items():
            try:
                setattr(file_meta, k, getattr(dcm.file_meta, v))
            except:
                log.warning(f"Could not transfer tag for keyword {k}")

        log.debug('Build non-meta-info which needs to transferred to new dicoms')
        series_manu_offset = 0
        if dcm.Manufacturer == 'Philips Medical Systems':
            series_manu_offset = 20
        elif (dcm.Manufacturer.lower() == 'siemens') | (dcm.Manufacturer == 'GE MEDICAL SYSTEMS'):
            series_manu_offset = 1000

        elements_to_define = {
            'Format': 'DICOM',
            'FormatVersion': 3,
            'Width': 3504,
            'Height': 2479,
            'BitDepth': 3,
            'ColorType': 'truecolor',
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.7',
            'Modality': 'MR',
            'ConversionType': 'WSD',
            'TimeofSecondaryCapture': '',
            'SecondaryCaptureDeviceManufacturer': 'Tarquin',
            'SecondaryCaptureDeviceManufacturerModelName': '4.3.6',
            'SecondaryCaptureDeviceSoftwareVersion': '4.3.6',
            'SOPInstanceUID': unique_uid,
            'SeriesInstanceUID': pyd.uid.generate_uid(),
            'SeriesNumber': dcm.SeriesNumber + series_manu_offset,
            'InstanceNumber': 1,
            'SamplesPerPixel': 3,
            'PhotometricInterpretation': 'RGB',
            'PlanarConfiguration': 0,
            'Rows': 2479,
            'Columns': 3504,
            'BitsAllocated': 8,
            'BitsStored': 8,
            'HighBit': 7,
            'PixelRepresentation': 0,
            'LossyImageCompression': '00',
        }

        elements_to_transfer = {'FileModDate': 'FileModDate',
                                'SpecificCharacterSet': 'SpecificCharacterSet',
                                'StudyDate': 'StudyDate',
                                'SeriesDate': 'SeriesDate',
                                'AcquisitionDate': 'StudyDate',
                                'StudyTime': 'StudyTime',
                                'AcquistionTime': 'StudyTime',
                                'AccessionNumber': 'AccessionNumber',
                                'PatientID': 'PatientID',
                                'PatientBirthDate': 'PatientBirthDate',
                                'PatientSex': 'PatientSex',
                                'DateofSecondaryCapture': 'StudyDate',
                                'StudyInstanceUID': 'StudyInstanceUID',
                                'StudyID': 'StudyID',
                                'PerformedProcedureStepDescription': 'PerformedProcedureStepDescription',
                                'ReferringPhysicianName': 'ReferringPhysicianName',
                                'OperatorName': 'OperatorName',
                                'PatientName': 'PatientName'}

        # Conditional Tags
        if dcm.data_element('StudyDescription') is not None:
            elements_to_transfer['StudyDescription'] = 'StudyDescription'

        if dcm.data_element('SeriesDescription') is not None:
            elements_to_define['SeriesDescription'] = 'Tarquin_' + dcm.SeriesDescription
            elements_to_define['ProtocolName'] = 'Tarquin_' + dcm.SeriesDescription
        else:
            elements_to_define['SeriesDescription'] = 'Tarquin'
            elements_to_define['ProtocolName'] = 'Tarquin'

        # Create the Dataset instance (initially no data elements, but file_meta supplied)
        ds = pyd.Dataset()
        ds.file_meta = file_meta
        ds.is_implicit_VR = False
        ds.is_little_endian = True

        # Add the data elements to the
        for k, v in elements_to_define.items():
            setattr(ds, k, v)

        for k, v in elements_to_transfer.items():
            try:
                setattr(ds, k, getattr(dcm, v))
            except:
                log.warning(f"Could not transfer tag for keyword {k}")

        log.debug('Add MRS PNGs to DICOM')
        png_counter = len(glob.glob1(self.job_results_dir, "*.png"))
        if png_counter == 1:
            im1 = Image.open(os.path.join(self.job_results_dir, self.png_filename + '.png'))
            im1 = im1.convert('RGB')

            setattr(ds, 'PixelData', im1.tobytes())
            ds.save_as(os.path.join(self.job_results_dir, self.output_filename_root + '_Tarquin_Output.dcm'),
                       write_like_original=False)

        elif png_counter > 1:
            im1 = Image.open(os.path.join(self.job_results_dir, self.png_filename + '-0.png'))
            im2 = Image.open(os.path.join(self.job_results_dir, self.png_filename + '-1.png'))

            im1 = im1.convert('RGB')
            im2 = im2.convert('RGB')

            # Create for second dicom object
            ds2 = copy.deepcopy(ds)
            unique_uid2 = pyd.uid.generate_uid()
            ds2.InstanceNumber = ds.InstanceNumber + 1
            ds2.file_meta.MediaStorageSOPInstanceUID = unique_uid2
            ds2.SOPInstanceUID = unique_uid2

            log.debug('Media UID of File 1 = ' + ds.file_meta.MediaStorageSOPInstanceUID)
            log.debug('Media UID of File 2 = ' + ds2.file_meta.MediaStorageSOPInstanceUID)
            log.debug('SOP UID of File 1 = ' + ds.SOPInstanceUID)
            log.debug('SOP UID of File 2 = ' + ds2.SOPInstanceUID)

            setattr(ds, 'PixelData', im1.tobytes())
            ds.save_as(os.path.join(self.job_results_dir, self.output_filename_root + '_Tarquin_Output.dcm'),
                       write_like_original=False)

            setattr(ds2, 'PixelData', im2.tobytes())
            ds2.save_as(
                os.path.join(self.job_results_dir, self.output_filename_root + '_Tarquin_Output_Extended_Plot.dcm'),
                write_like_original=False)

        else:
            raise Exception('No png files to convert to DICOMs')

        return

    def process_siemens_qa_data(self):

        log.debug('Running process_siemens_qa_data')

        n_reject = 50
        n_pad_factor = 3

        # Suppressed Spectrum
        data_raw = np.array(self.water_sup_series.dicom_list[0].SpectroscopyData, dtype=np.float32)

        data_complex = data_raw[0::2] + 1j * data_raw[1::2]
        data_complex = data_complex[n_reject:-n_reject]
        data_complex = np.pad(data_complex, (0, n_pad_factor * data_complex.size), 'constant', constant_values=0)
        data = np.fft.fftshift(np.fft.fft(data_complex))

        # Unsuppressed Spectrum
        data_wr_raw = np.array(self.water_ref_series.dicom_list[0].SpectroscopyData, dtype=np.float32)
        data_wr_complex = data_wr_raw[0::2] + 1j * data_wr_raw[1::2]
        data_wr_complex = data_wr_complex[n_reject:-n_reject]
        data_wr_complex = np.pad(data_wr_complex, (0, n_pad_factor * data_wr_complex.size), 'constant',
                                 constant_values=0)
        data_wr = np.fft.fftshift(np.fft.fft(data_wr_complex))

        # Make frequency axes for water suppressed
        f0 = self.water_sup_series.dicom_list[0].TransmitterFrequency * 1e6
        sw_hz = self.water_sup_series.dicom_list[0].SpectralWidth
        sw_ppm = sw_hz * 1e6 / f0
        csr_hz = f0
        csr_ppm = self.water_sup_series.dicom_list[0].ChemicalShiftReference
        f_axis_hz = np.linspace(csr_hz - sw_hz / 2, csr_hz + sw_hz / 2, data.size)
        f_axis_ppm = np.linspace(csr_ppm - sw_ppm / 2, csr_ppm + sw_ppm / 2, data.size)

        # Make frequency axes for water unsuppressed
        f0 = self.water_ref_series.dicom_list[0].TransmitterFrequency * 1e6
        sw_hz = self.water_ref_series.dicom_list[0].SpectralWidth
        sw_ppm = sw_hz * 1e6 / f0
        csr_hz = f0
        csr_ppm = self.water_ref_series.dicom_list[0].ChemicalShiftReference
        f_axis_hz_wr = np.linspace(csr_hz - sw_hz / 2, csr_hz + sw_hz / 2, data_wr.size)
        f_axis_ppm_wr = np.linspace(csr_ppm - sw_ppm / 2, csr_ppm + sw_ppm / 2, data_wr.size)

        # Noise
        ppm_lim1 = 0.0
        ppm_lim2 = 0.5
        std_ace = np.std(np.real(data_complex[abs(f_axis_ppm - ppm_lim1).argmin():abs(f_axis_ppm - ppm_lim2).argmin()]))
        std_h20 = np.std(
            np.real(data_wr_complex[abs(f_axis_ppm - ppm_lim1).argmin():abs(f_axis_ppm - ppm_lim2).argmin()]))

        # Calculate Metrics
        h2o_sig = max(abs(data_wr))
        ace_sig = max(abs(data))
        h2o_loc = f_axis_ppm_wr[np.argmax(np.abs(data_wr))]
        ace_loc = f_axis_ppm[np.argmax(np.abs(data))]
        h2o_fwhm = fwhm(f_axis_hz, abs(data_wr))
        ace_fwhm = fwhm(f_axis_hz_wr, abs(data))
        h2o_snr = h2o_sig / std_h20
        ace_snr = ace_sig / std_ace

        res_v = np.array([h2o_snr, ace_snr, h2o_loc, ace_loc, h2o_fwhm, ace_fwhm])

        return res_v

    def archive_siemens_qa(self, dv):

        log.debug('Running archive_siemens_qa')

        # Check that only single values being passed to archive
        if dv.shape != (6,):
            raise TypeError

        h2o_snr, ace_snr, h2o_loc, ace_loc, h2o_fwhm, ace_fwhm = tuple(dv.tolist())

        # If file DB folder doesn't exist
        os.makedirs(self.qa_dir, exist_ok=True)

        # If QA database file DOESN'T exist....
        if os.path.exists(self.qa_db_full_filename) is False:
            # ...create it with correct column headers
            with open(self.qa_db_full_filename, 'w') as f:
                # Make object which can write to file
                file_writer = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

                # Write row with column headers
                file_writer.writerow(
                    ['Scan Date', 'Scan Time', 'Scan DOY', 'Processing Date', 'Processing Time', 'H2O - SNR',
                     'Acetone - SNR ', 'H2O - Frequency', 'Acetone - Frequency', 'H2O - FWHM', 'Acetone - FWHM'])

        # Irrespective of if QA database file DOES or DOES NOT exist...
        # Open file in append mode
        with open(self.qa_db_full_filename, 'a') as f:

            # Create file_writer object
            file_writer = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

            # These objects contain times
            now = datetime.datetime.now()
            study_time = datetime.datetime.strptime(
                self.water_sup_series.dicom_list[0].StudyDate + self.water_sup_series.dicom_list[0].StudyTime[0:5],
                '%Y%m%d%H%M%S')

            # Write header
            file_writer.writerow(
                [str(study_time.strftime('%Y%m%d')), str(study_time.strftime('%H%M%S')), str(study_time.strftime('%j')),
                 str(now.strftime('%Y%m%d')), str(now.strftime('%H%M%S')), str(h2o_snr), str(ace_snr), str(h2o_loc),
                 str(ace_loc), str(h2o_fwhm), str(ace_fwhm)])

    def report_siemens_qa(self):

        log.debug('Reporting Results')

        # First open database file
        with open(self.qa_db_full_filename, 'r') as f:

            # Now read it in
            filereader = csv.reader(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

            # Skip first line, which is the header
            next(filereader)

            # Go through all lines
            data = [r for r in filereader]

        log.debug('Data successfully imported')

        #  Convert data list of lists to numpy array for plotting
        data = np.array(data)

        #  Make data vectors
        doy_v = np.ndarray.astype(data[:, 2], dtype=float)
        h2o_snr_v = np.ndarray.astype(data[:, 5], dtype=float)
        ace_snr_v = np.ndarray.astype(data[:, 6], dtype=float)
        h2o_freq_v = np.ndarray.astype(data[:, 7], dtype=float)
        ace_freq_v = np.ndarray.astype(data[:, 8], dtype=float)
        h2o_fwhm_v = np.ndarray.astype(data[:, 9], dtype=float)
        ace_fwhm_v = np.ndarray.astype(data[:, 10], dtype=float)

        log.debug('Ready to analyse')

        # Do analysis
        h2o_snr_ao = analysis(h2o_snr_v)
        ace_snr_ao = analysis(ace_snr_v)
        h2o_freq_ao = analysis(h2o_freq_v)
        ace_freq_ao = analysis(ace_freq_v)
        h2o_fwhm_ao = analysis(h2o_fwhm_v)
        ace_fwhm_ao = analysis(ace_fwhm_v)

        log.debug('Data successfully analysed')

        #  Generate plots
        h2o_snr_f1, h2o_snr_f2 = make_qa_plots(self.job_results_dir, doy_v, h2o_snr_v, 'H2O_SNR')
        ace_snr_f1, ace_snr_f2 = make_qa_plots(self.job_results_dir, doy_v, ace_snr_v, 'Acetone_SNR')
        h2o_freq_f1, h2o_freq_f2 = make_qa_plots(self.job_results_dir, doy_v, h2o_freq_v, 'H2O_Frequency')
        ace_freq_f1, ace_freq_f2 = make_qa_plots(self.job_results_dir, doy_v, ace_freq_v, 'Acetone_Frequency')
        h2o_fwhm_f1, h2o_fwhm_f2 = make_qa_plots(self.job_results_dir, doy_v, h2o_fwhm_v, 'H2O_FWHM')
        ace_fwhm_f1, ace_fwhm_f2 = make_qa_plots(self.job_results_dir, doy_v, ace_fwhm_v, 'Acetone_FWHM')

        log.debug('Plots successfully made and saved')

        # Send email
        mail_recipients = SETTINGS['mrs']['qa_email_list']
        subject = 'MRS QA Results'

        if h2o_snr_ao & ace_snr_ao & h2o_freq_ao & ace_freq_ao & h2o_fwhm_ao & ace_fwhm_ao is True:

            message = "QA PASSED. Please review results attached. This is an automated email sent by dicomserver (https://bitbucket.org/gsttmri/dicomserver)"

        else:

            message = "QA FAILED. Please review results attached. This is an automated email sent by dicomserver (https://bitbucket.org/gsttmri/dicomserver)"

        attachments = [h2o_snr_f1, h2o_snr_f2, ace_snr_f1, ace_snr_f2, h2o_freq_f1, h2o_freq_f2, ace_freq_f1,
                       ace_freq_f2, h2o_fwhm_f1, h2o_fwhm_f2, ace_fwhm_f1, ace_fwhm_f2]

        try:
            myemail.nhs_mail([mail_recipients], subject, message, attachments)
            log.debug('Emails successfully sent')
        except:
            log.debug('Emails could not be sent')
            raise

        return 0
