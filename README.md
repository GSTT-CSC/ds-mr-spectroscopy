# MR Spectroscopy

Clinical MRS at the end of a standard MRI examination obtains functional information in addition to anatomical information. 
MRI forms pictures of anatomy of the body using strong magnetic fields, magnetic field gradients and radio waves. 
MRS detects radio frequency electromagnetic signals produced by atomic nuclei within molecules, which can obtain in situ concentration measures for certain chemicals. 
In this way, MRI can identify tumour anatomical location, whilst MRS can be used to compare the chemical composition of normal brain tissue with abnormal tumour tissue.

Single-voxel spectroscopy (SVS) techniques are the simplest techniques to acquire and intepret so are the most widely used. 
They provide a high signal-to-noise ratio in a short scan time.

## Project Proposal

### Clinical Background

Clinical MRS at the end of a standard MRI examination obtains functional information in addition to anatomical information. 
MRI forms pictures of anatomy of the body using strong magnetic fields, magnetic field gradients and radio waves. 
MRS detects radio frequency electromagnetic signals produced by atomic nuclei within molecules, which can obtain in situ concentration measures for certain chemicals. 
In this way, MRI can identify tumour anatomical location, whilst MRS can be used to compare the chemical composition of normal brain tissue with abnormal tumour tissue.

Single-voxel spectroscopy (SVS) techniques are the simplest techniques to acquire and intepret so are the most widely used. 
They provide a high signal-to-noise ratio in a short scan time.

### The Clinical Setting

MR Spectroscopy data is primarily acquired in an outpatient setting but can also be acquired in inpatients. Data acquistion is performed by the Radiology department
using an MR scanner. Results are sent to Picture Archiving and Communication System (PACS) to allow the Radiologists to report on the results. The results are then
used in the management of patient's disease.

### The Problem

The MR Spectroscopy analysis that is provided by the MRI machine manufacturer is not of the best scientific quality and there are better methods available now.
Therefore, it is required to implement the TARQUIN package as a dicomserver plugin in order to more accurately determine the quantities of molecules present in 
MR Spectroscopy data.

### Key Stakeholders

- Radiologists: report on the results
- Radiographers: send data for analysis
- MR Physicists: manage analysis and verify results

### End Users
- Radiologists

### Clinical Information Systems involved

- MR Scanners: acquire and send data
- dicomserver: post-processing server that receives data and can trigger processing jobs
- PACS: radiology data archiving and report system


