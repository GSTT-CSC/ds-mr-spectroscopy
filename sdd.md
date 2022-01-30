# System Design Specification

## Purpose

This document describes the detailed designs derived from the requirements defined in [srs.md](srs.md) and [hazard-log.md](hazard-log.md).

## Scope

The scope of this document is limited to the design of the MRSpectroscopy analysis software. This design document does not address any design decisions belonging to other subsystems, such as dicomserver.

## Specification

### SDS-001
Addresses: SRS001, SRS003, HZD001, HZD003.

The software shall be written as a dicomserver plugin. This means writing the analysis code as a subclass of the dicomserver ProcessTask abstract class. This permits
the software to receive dicom data from MR Scanners. It also ensures that the analysis is executed automatically allowing it to meet the turnaround of 10 minutes 
from SRS003.

![architecture](https://user-images.githubusercontent.com/19840489/151717520-e19142be-3879-4194-8730-4163c70b9e01.png)

Figure 1. System architecture

### SDS-002
Addresses: SRS002

The software shall convert the analysis report into a PDF and use an appropriate library, e.g. [pydicom](www.pydicom.com), to create a dicom encapsulated PDF.

### SDS-003
Addresses: SRS004

The software shall use the (Tarquin)[http://tarquin.sourceforge.net] software to perform the metabolite fitting and quantification.

### SDS-004
Addresses: HZD002

The software shall use test data with known metabolite quantities to perform regression and accuracy testing.
