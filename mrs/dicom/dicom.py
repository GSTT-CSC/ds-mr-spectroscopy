import pydicom
from pydicom.dataset import FileDataset


class Dicom(FileDataset):
    """
    Base DICOM class that uses `pydicom <https://pydicom.github.io>`_ library to read raw DICOM file. This class is considered private and should not
    be instantiated directly by ProcessTask developers.

    Given a ``dicomserver.dicom.Dicom`` object, the developer is able to access dicom tag data using the syntax documented
    in the ``pydicom`` library::

        from dicomserver.dicom import Dicom

        my_dicom = Dicom(f=filepath)
        my_array = my_dicom.pixel_array
    """
    def __init__(self, f):
        self._data = pydicom.read_file(f)
        self.path = f
        FileDataset.__init__(self,
                             filename_or_obj=f,
                             dataset=self._data,
                             file_meta=self._data.file_meta,
                             preamble=self._data.preamble,
                             is_implicit_VR=self._data.is_implicit_VR,
                             is_little_endian=self._data.is_little_endian
                             )

    def __str__(self):
        return "Dicom('{}')".format(self._data.filename)

    def __repr__(self):
        return self.__str__()