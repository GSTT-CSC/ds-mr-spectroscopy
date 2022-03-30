import os
import datetime
import re
import sys
import matplotlib.pyplot as pyp
import pandas as pd
import numpy as np

from mrs.tools.exceptions import InvalidInputData
from config.config import SETTINGS
from aide_sdk.logger.logger import LogManager
from mrs.dicom.series import Series
from mrs.dicom.study import Study

log = LogManager.get_logger()


def calc_mean_xcorr(patient: pd.DataFrame, normal_list: list):  # pragma: no cover

    xcorr = []  # cross-correlation

    p_fit = patient['Fit']  # post-processed amplitude data

    for normal in normal_list:
        df = pd.read_csv(normal)
        norm_fit = df['Fit']

        # calculate xcorr and store it to list to be averaged later
        m = [a * b for a, b in
             zip(p_fit, norm_fit)]  # multiplication in f-domain = time-reversed convolution in t-domain
        xcorr.append(np.fft.ifft(m))

    return np.mean(xcorr)


def check_valid_mrs(study: Study) -> bool:
    for series in study.series_list:
        for dcm in series.dicom_list:
            if is_mrs(dcm):
                return True
    else:
        return False


def is_mrs(dcm) -> bool:
    """
    .. todo:: Add GE support

    Parameters
    ----------
    dicom - dicom which is being checked to see if it's a valid MRS dicom

    Returns
    -------

    """

    if dcm.SeriesDescription is not None:

        if dcm.Manufacturer == 'Philips Medical Systems':

            try:

                if dcm.PulseSequenceName == 'SPECTROSCOPY':

                    log.warn('Found Philips MRS data')
                    return True
                else:

                    return False

            except Exception:

                try:
                    if dcm['2005', '140f'][0]['0018', '9005'].value == 'SPECTROSCOPY':

                        log.warn('Found Philips MRS data')
                        return True
                    else:
                        return False

                except Exception:

                    log.warning('Did not find PulseSequenceName tag')
                    raise InvalidInputData
                    # This shouldn't raise an error because SC, RAW data will break if this is uncaught
                    # Later message: I decided to keep this as the process function now catches this

        elif (dcm.Manufacturer.lower() == 'siemens'):

            # This condition ensures that the data is in Enhanced DICOM format
            if 'ORIGINAL' in dcm.ImageType and 'SPECTROSCOPY' in dcm.ImageType:
                with open(dcm.filename, 'rb') as f:

                    for line in f:

                        if line.startswith(b'tSequenceFileName'):
                            if line.endswith(b'svs_se""\n'):
                                log.warn('Found Siemens MRS data')
                                return True
                            else:
                                log.warn('This is not MRS data: {line}'.format(**locals()))
                                return False

                    else:
                        log.warning('Could not find tSequenceFileName in CSA header')
                        raise InvalidInputData

    return False


def get_voxel_size(series: Series):
    log.warn('Running get_voxel_size function')

    dcm = series.dicom_list[0]

    vox_x, vox_y, vox_z = '', '', ''
    if dcm.Manufacturer == 'Philips Medical Systems':

        try:
            vox_x = str(
                series.dicom_list[0].PerFrameFunctionalGroupsSequence[0].PixelMeasuresSequence[0].PixelSpacing[0])
            vox_y = str(
                series.dicom_list[0].PerFrameFunctionalGroupsSequence[0].PixelMeasuresSequence[0].PixelSpacing[1])
            vox_z = str(series.dicom_list[0].VolumeLocalizationSequence[0].SlabThickness)
        except Exception:
            log.warning('Philips: Did not find voxel sizes')
            raise ValueError

    elif dcm.Manufacturer.lower() == 'siemens':
        with open(dcm.filename, 'rb') as f:

            for line in f:
                if line.find(b'sSpecPara.sVoI.dThickness') > -1:
                    vox_x = re.findall(r'\d+\.?\d*(?=\\)', str(line))
                if line.find(b'sSpecPara.sVoI.dPhaseFOV') > -1:
                    vox_y = re.findall(r'\d+\.?\d*(?=\\)', str(line))
                if line.find(b'sSpecPara.sVoI.dReadoutFOV') > -1:
                    vox_z = re.findall(r'\d+\.?\d*(?=\\)', str(line))
            if not (vox_x and vox_y and vox_z):
                log.warning('Could not find all voxels. Found: {voxels}'.format(
                    voxels=[x for x in [vox_x, vox_y, vox_z] if x is not None]))
                raise Exception('Could not find voxel sizes')

    else:
        log.warning('Error: Not Siemens nor Philips')
        raise ValueError

    vox = [vox_x[0], vox_y[0], vox_z[0]]

    return vox


def get_tf_mhz(series: Series):
    log.warn('Running get_tf_mhz function to get the transmitter frequency in MHz')

    dcm = series.dicom_list[0]
    tf = 0.
    if dcm.Manufacturer == 'Philips Medical Systems':
        try:
            tf = series.dicom_list[0].TransmitterFrequency
        except Exception:
            log.warning('Philips: Did not find tf')
            raise ValueError
    else:
        log.warning('Error: Not Philips')
        raise Exception('Error: Not Philips')

    return tf


def get_te_ms(series: Series):
    log.warn('Running get_te_ms function')

    dcm = series.dicom_list[0]
    n_digits = 2

    te_ms = ''
    if dcm.Manufacturer == 'Philips Medical Systems':

        try:
            te_ms = str(
                round(series.dicom_list[0].PerFrameFunctionalGroupsSequence[0].MREchoSequence[0].EffectiveEchoTime,
                      n_digits))
        except Exception:
            log.warning('Philips: Did not find TE')
            raise ValueError

    elif dcm.Manufacturer.lower() == 'siemens':

        with open(dcm.filename, 'rb') as f:

            for line in f:
                if line.find(b'alTE[0]') > -1:
                    te = re.findall(r'\d+\.?\d*(?=\\)', str(line))
                    te_ms = str(round(float(te[0]) / 1000, n_digits))

            if not te_ms:
                log.warning('Siemens: did not find TE')
                raise InvalidInputData
    else:
        log.warning('Error: Not Siemens nor Philips')
        raise Exception('Error: Not Siemens nor Philips')

    return te_ms


def fwhm(axis, data):
    log.warn('Running fwhm calculation function')
    max_sig = np.amax(data)
    max_loc = np.argmax(data)

    approx_lhs_ind = max_loc
    while data[approx_lhs_ind] > max_sig / 2:
        approx_lhs_ind = approx_lhs_ind - 1
    m = (data[approx_lhs_ind + 1] - data[approx_lhs_ind]) / (axis[approx_lhs_ind + 1] - axis[approx_lhs_ind])
    c = data[approx_lhs_ind + 1] - m * axis[approx_lhs_ind + 1]
    lhs = (max_sig / 2 - c) / m

    approx_rhs_ind = max_loc
    while data[approx_rhs_ind] > max_sig / 2:
        approx_rhs_ind = approx_rhs_ind + 1
    m = (data[approx_rhs_ind] - data[approx_rhs_ind - 1]) / (axis[approx_rhs_ind] - axis[approx_rhs_ind - 1])
    c = data[approx_rhs_ind] - m * axis[approx_rhs_ind]
    rhs = (max_sig / 2 - c) / m

    res = rhs - lhs

    return res


def analysis(x):
    log.warn('Running analysis')

    if abs(x[-1] - x.mean()) > float(SETTINGS['mrs']['stat_thresh']) * x.std():

        # If the latest measurement lies outside a certain number of std, fail QA
        out = False

    else:

        # If not, pass QA
        out = True

    return out


def make_qa_plots(qa_series_folder, x, y, datatype):
    log.warn('Running make_qa_plots')

    # Make time object
    now = datetime.datetime.now()

    filename1 = os.path.join(qa_series_folder, datatype + now.strftime('_%Y%m%d_') + 'Whole_Year.png')
    filename2 = os.path.join(qa_series_folder, datatype + now.strftime('_%Y%m%d_') + 'Last_Month.png')

    # Plot data from year to date
    pyp.plot(x, y, 'ro')
    pyp.axis([0, 366, 0, 2 * max(y)])
    pyp.title(datatype + ' - Whole Year')
    pyp.plot(np.array([0, 366]), np.array([1, 1]) * y.mean(), color='k')
    pyp.plot(np.array([0, 366]), np.array([1, 1]) * (y.mean() + y.std()), color='k', linestyle='dashed')
    pyp.plot(np.array([0, 366]), np.array([1, 1]) * (y.mean() - y.std()), color='k', linestyle='dashed')
    pyp.xlabel('Day of Year')
    pyp.savefig(filename1)

    # Plot data from last month
    ax_min = max(x[-1] - 31, x[0])
    ax_max = x[-1]
    if ax_min == ax_max:
        ax_min = ax_min - 1
        ax_max = ax_max + 1

    pyp.axis([ax_min, ax_max, 0, 2 * np.max(y)])
    pyp.title(datatype + ' - Last Month')
    pyp.xlabel('Day of Year')
    pyp.savefig(filename2)

    # Clear axes for next plot
    pyp.clf()

    return filename1, filename2


def identify_siemens_mrs_series_type(series) -> str:
    """

    Parameters
    ----------
    series: dicomserver.dicom.Series
        This is the Siemens series which you want to determine the mrs type of

    Returns
    -------
    mrs_series_type : str
        String describing the MRS series type (water_reference, water_suppressed_ECC, water_suppressed_noECC, or water_suppressed)
    """

    mrs_series_type = []

    if (series.manufacturer.lower() != 'siemens'):
        raise Exception('Series of wrong manufacturer passed to identify_siemens_mrs_series_type')

    if '_ref' in series.dicom_list[0].SeriesDescription:
        mrs_series_type = 'water_reference'
    elif '_ECC' in series.dicom_list[0].SeriesDescription:
        mrs_series_type = 'water_suppressed_ECC'
    elif '_noECC' in series.dicom_list[0].SeriesDescription:
        mrs_series_type = 'water_suppressed_noECC'
    elif 'svs_se_30_H2O_1NSA_2048_TRIPLE' in series.dicom_list[0].SeriesDescription:
        mrs_series_type = 'water_reference'
    elif 'svs_se_30_NSA4_2048_TRIPLE' in series.dicom_list[0].SeriesDescription:
        mrs_series_type = 'water_suppressed'
    else:
        with open(series.dicom_list[0].filename, 'rb') as f:
            for line in f:
                if line.find(b'sPrepPulses.ucWaterSat') > -1:
                    wat_sat_str = re.findall(r'\d+(?=\\)|\dx\d*', str(line))[0]
                    if (wat_sat_str == '1') or (wat_sat_str == '0x1'):
                        mrs_series_type = 'water_suppressed'
                    elif (wat_sat_str == '64') or (wat_sat_str == '0x40'):
                        mrs_series_type = 'water_reference'
                    else:
                        raise Exception('Cannot find expected strings in CSA header for water saturation pulse status')
                    break
            else:
                raise Exception('Could not find sPrepPulses.ucWaterSat in dicom file')
    return mrs_series_type


# if we are testing and not running then use different config file
def is_under_test() -> bool:
    return 'pytest' in sys.modules
