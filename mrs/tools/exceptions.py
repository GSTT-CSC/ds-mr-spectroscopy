"""Application-specific exception classes"""


class MissingOtherMRS(Exception):
    """Missing either water-suppressed or unsuppressed MRS"""


class InvalidInputData(Exception):
    """The input dicom or series does not meet necessary criteria"""
