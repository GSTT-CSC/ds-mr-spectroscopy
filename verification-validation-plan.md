# Verification and Validation Plan

## Purpose
The verification plan lists verification actions that must be performed as part of the design plan. The verification activities play a part in successful 
risk management mitigations and regulatory compliance in medical software development. The validation process consists of high level tests and checks that makes 
sure the solution fits the requirements of all stakeholders.


## Verification
The analysis of the MR Spectroscopy data is delegated to Tarquin and so the vast majority of verification checks can only be performed qualitatively once the analysis
report is returned by Tarquin. 

The results of all analysis should interpreted by an MR Physicist who is an expert in MR Spectroscopy analysis and who can verify the quality of fit of the analysis.

## Validation
The user should perform the following tests to ensure that software meets requirements:
- send MR Spectroscopy data to dicomserver and check if the result is returned to PACS within 10 minutes
- check that the result in PACS is a valid DICOM file
- check that the MRSpectroscopy analysis performed performs a more accurate quantification of metabolites.
