import os

# 3rd party modules

# Package modules
from mrs.dicom.series import Series
from mrs.tools.exceptions import InvalidInputData
from aide_sdk.logger.logger import LogManager

log = LogManager.get_logger()


class Study:
    """
    Base class for received MRI Study. This class is considered private and should not be instantiated directly by
    ProcessTask developers.

    Given a ``dicomserver.dicom.Study`` object, the developer is able to access study level data as well as access the
    individual ``Series`` and ``Dicom`` objects that the study is composed of::

        from dicomserver.dicom import Study

        my_study = Study(dicom_list=[list_of_dicomserver_dicoms])

        print(f"Study has UID of {my_study.study_uid} and contains: \\n
             {','.join(my_study.series_list)}")

    Attributes
    ----------
    subject_id
    subject_name
    study_date
    """
    def __init__(self, **kwargs):

        self._series_list = kwargs.get('series_list', None)
        self._study_dir = kwargs.get('study_dir', None)
        self._dicom_list = kwargs.get('dicom_list', None)

        if self._study_dir and self._series_list:
            raise AttributeError("Both _study root directory and series list provided. "
                                 "Please provide only one.")

        elif self._study_dir:
            log.warn('Constructing Study from study dir {self._study_dir}'.format(**locals()))
            self._series_list = _get_list_of_series_(self._study_dir)

        elif self._dicom_list:
            log.warn('Constructing Study from Dicom list {self._dicom_list}'.format(**locals()))
            self._series_list = _get_list_of_series_from_dicom_(self._dicom_list)

        try:
            res = self.valid
            pass
        except IndexError:
            raise InvalidInputData('Could not access first series or first dicom:\n'
                                   'series_list: {self._series_list}'.format(**locals()))

        if not res:
            raise InvalidInputData

    def __str__(self):
        return 'Study({})'.format(self.study_uid)

    def __repr__(self):
        return self.__str__()

    @property
    def valid(self):
        """
        Iterates over every dicom in every series in the study and ensures that the StudyInsanceUID is identical.

        Returns
        -------
        bool
        """
        uid = self._series_list[0].dicom_list[0].StudyInstanceUID
        for series in self._series_list:
            for dicom in series.dicom_list:
                if dicom.StudyInstanceUID != uid:
                    return False
        return True

    @property
    def study_uid(self):
        """
        Reads StudyInstanceUID from the first dicom in the first series.

        Returns
        -------
        StudyInstanceUID : str

        Raises
        ------
        AttributeError
        InvalidInputData

        """
        if self.valid:
            try:
                return self._series_list[0].dicom_list[0].StudyInstanceUID
            except:
                raise AttributeError("Valid _study UID could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def accession_number(self):
        try:
            return self._series_list[0].dicom_list[0].AccessionNumber
        except:
            raise InvalidInputData

    @property
    def subject_id(self):
        if self.valid:
            try:
                return self._series_list[0].dicom_list[0].PatientID
            except:
                raise AttributeError("Valid patient ID could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def subject_name(self):
        if self.valid:
            try:
                return str(self._series_list[0].dicom_list[0].PatientName)
            except:
                raise AttributeError("Valid PatientName could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def study_date(self):
        if self.valid:
            try:
                return self._series_list[0].dicom_list[0].StudyDate
            except:
                raise AttributeError("Valid _study date could not be found for {self}".format(**locals()))
        else:
            raise InvalidInputData

    @property
    def manufacturer(self):
        if self.valid:
            return self._series_list[0].dicom_list[0].Manufacturer
        else:
            raise InvalidInputData

    @property
    def directory_tree(self):
        """
        Returns directory made from ``Study.subject_id`` and ``Study.study_date`` in order to facilitate
        creation of subdirectory tree for study files organisation.

        Returns
        -------
        self.directory_tree : dict

        """
        if self.valid:
            return {'subject': self.subject_id,
                    'date': self.study_date}
        else:
            raise AttributeError

    @property
    def directory_path(self):
        """
        Returns file path constructed from directory_tree

        Returns
        -------
        path : str

        """
        if self.valid:
            return os.path.join(*[x for x in self.directory_tree.values()])

    @property
    def series_list(self):
        """
        Returns list of ``dicomserver.Series`` objects that make up the study

        Returns
        -------
        self._series_list : list of dicomserver.Series
        """
        return self._series_list


def _get_list_of_series_(root_dir) -> [Series]:
    """
    Performs walk down root directory and assumes each sub directory is a series and creates a Series object of each
    using the dicoms in each of these subdirectories and makes sure they are valid.  
    
    Parameters
    ----------
    root_dir

    Returns
    -------
    
    Raises
    -----
    InvalidInputData
    """

    series_list = []

    for root, dirs, files in os.walk(root_dir):

        for directory in dirs:
            try:
                series_list.append(Series(series_dir=os.path.join(root, directory)))
                log.warn(series_list)
            except:
                raise

    return series_list


def _get_list_of_series_from_dicom_(dicom_list) -> [Series]:
    """
    Returns a list of series from list of dicoms.
    
    Parameters
    ----------
    dicom_list

    Returns
    -------
    
    """
    series_dict = {}

    for dicom in dicom_list:

        try:
            series_uid = dicom.SeriesInstanceUID
        except:
            raise AttributeError("Valid series UID could not be found for {se}".format(**locals()))

        if series_uid not in series_dict.keys():
            # create new dictionary entry if series_uid doesn't exist as dictionary key
            series_dict[series_uid] = [dicom]
        else:
            # if series_uid exists then append this dicom to list for this series_uid
            series_dict[series_uid].append(dicom)

    # for every list of dicoms with the same series_uid return a series
    return [Series(dicom_list=dicoms) for dicoms in series_dict.values()]
