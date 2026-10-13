# PRESLHY raw-channel clarification request

Subject: Request for pressure-boundary and synchronization metadata for reproducible hydrogen blow-down validation

Dear PRESLHY/KIT data custodian,

We are preparing a reproducibility-bounded validation of a hydrogen release model using the public PRESLHY E3.1 Part-A dataset (DOI: [10.35097/1187](https://doi.org/10.35097/1187)) and the E5.1 benchmark dataset (DOI: [10.35097/1258](https://doi.org/10.35097/1258)). We will cite the public records and retain the stated CC BY or CC BY-SA terms.

Could you please clarify or provide, for the released workbooks, the following items?

1. **E3.1 cryogenic files (80 K packages)**
   - The measured ambient/barometric pressure channel or the documented absolute-pressure reference used during each run.
   - Whether the vessel-pressure channel is gauge or absolute, including the pressure transducer zero/reference procedure.
   - The release-time synchronization rule and the channel used to identify valve opening.
   - Any uncertainty or calibration information for the pressure and temperature channels.

2. **E5.1 benchmark files**
   - The source-pressure channel mapping for the two ambient experiments that cannot currently be mapped from the published workbook headers.
   - The common release-time marker linking the PFast and SE workbooks when their filenames differ by a few seconds.
   - Confirmation of nozzle diameter, initial pressure basis, and whether the source-pressure trace includes the post-ignition interval.

3. **Reuse and citation**
   - Confirmation that derived, non-redistributive error metrics and plots may be published under the license of each record.
   - A preferred citation and acknowledgement for the data custodian and facility.

We will not redistribute raw rows or identify individual facilities beyond the public dataset citation. The requested information will be used only to freeze a protocol before opening any additional numerical outcomes. If the missing channels cannot be released, a short statement confirming their unavailability would also help us document the validation boundary accurately.

Sincerely,

*[project author, affiliation, institutional email and project DOI to be supplied before sending]*

## Internal handling note

This draft is not evidence that the requested metadata exist or that any validation gate has passed. Do not send it until the project author supplies the sender identity and approved institutional contact. If a reply is received, archive the message and its attachments outside the public repository first; then create a pre-access protocol and hash the supplied files before reading numerical outcomes.
