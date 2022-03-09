import re
import os

import pydicom

from mrs.dicom.dicom import Dicom
from mrs.tools.exceptions import InvalidInputData
from aide_sdk.logger.logger import LogManager

log = LogManager.get_logger()


class Series:
    """
    Base class for MRI series. This class is considered private and should not be instantiated directly by ProcessTask
    developers.

    Given a ``dicomserver.dicom.Series`` object, the developer is able to access series level data as well as access the
    individual ``dicomserver.dicom.Dicom`` objects that the Series is composed of::

        from dicomserver.dicom import Series

        my_study = Study(dicom_list=[list_of_dicomserver_dicoms])

        for series in my_study.series_list:

            print(f"Series: {my_series.series_name} for {series.subject_name}, contains: {dcm.SOPInstanceUID}")
    """
    def __init__(self, **kwargs):
        self.dicom_list = kwargs.get('dicom_list', None)
        self.series_dir = kwargs.get('series_dir', None)
        self.valid = None

        if self.dicom_list and self.series_dir:
            raise AttributeError("Both series directory and dicom list provided. "
                                 "Please provide only one.")

        elif self.series_dir:
            self.dicom_list = _get_list_of_dicom_(self.series_dir)

        self._validate()

    def __str__(self):
        return "Series('{}')".format(self.series_name)

    def __repr__(self):
        return self.__str__()

    @property
    def subject_id(self):
        if self.valid:
            try:
                return self.dicom_list[0].PatientID
            except:
                raise AttributeError("Valid patient ID could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def subject_name(self):
        if self.valid:
            try:
                return str(self.dicom_list[0].PatientName).replace('^', "_").strip('_')
            except:
                raise AttributeError("Valid PatientName could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def study_date(self):
        if self.valid:
            try:
                return self.dicom_list[0].StudyDate
            except:
                raise AttributeError("Valid _study date could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def image_type(self):
        if self.valid:
            try:
                return self.dicom_list[0].ImageType
            except:
                raise AttributeError(f"Valid ImageType could not be found for {self}")

    @property
    def series_name(self):
        if self.valid:
            try:
                return re.sub(r'[^a-zA-Z0-9]', '_', self.dicom_list[0].SeriesDescription)
            except AttributeError:
                return "NoSERIES"

    @property
    def series_uid(self):
        if self.valid:
            try:
                return self.dicom_list[0].SeriesInstanceUID
            except:
                raise AttributeError("Valid _study UID could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def manufacturer(self):
        if self.valid:
            try:
                return self.dicom_list[0].Manufacturer
            except:
                raise AttributeError("Scanner manufacturer could not be found")

    @property
    def directory_tree(self):
        if self.valid:
            return {'subject': self.subject_id,
                    'date': self.study_date,
                    'series': self.series_name}
        else:
            raise AttributeError

    def _validate(self):

        series_instance_uid = self.dicom_list[0].SeriesInstanceUID

        for dicom in self.dicom_list:
            if series_instance_uid != dicom.SeriesInstanceUID:
                self.valid = False
                raise InvalidInputData

        self.valid = True

    @property
    def max_pixel_intensity(self):

        max_intensity = 0.0

        for dicom in self.dicom_list:

            dicom_max = dicom.LargestImagePixelValue

            max_intensity = dicom_max if dicom_max > max_intensity else max_intensity

        return max_intensity

    @property
    def min_pixel_intensity(self):

        min_intensity = 100000

        for dicom in self.dicom_list:

            dicom_max = dicom.SmallestImagePixelValue
            print(min_intensity)
            min_intensity = dicom_max if dicom_max < min_intensity else min_intensity

        return min_intensity


def _get_list_of_dicom_(directory) -> [Dicom]:
    """
    This returns a list of Dicom objects from a directory of dicom files that belong to the same series.
    
    ..note:: There is no guarantee that this list represents the complete list of dicoms for that series.
    
    Parameters
    ----------
    directory

    Returns
    -------
    dicom_list: [Dicom]
    
    Raises
    -----
    InvalidInputData

    """
    dicom_list = []

    for item in os.listdir(directory):

        if item == '.DS_Store' or os.path.isdir(item):
            continue

        file_path = os.path.join(directory, item)

        try:
            _ = pydicom.read_file(file_path)
        except:
            raise
        else:
            dicom_list.append(Dicom(f=file_path))

    return dicom_list
