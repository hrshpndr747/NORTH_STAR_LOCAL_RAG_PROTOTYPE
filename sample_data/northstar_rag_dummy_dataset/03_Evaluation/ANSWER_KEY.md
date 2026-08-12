# RAG Evaluation Answer Key

All information is fictional.

## Q01 - What are the standard office hours?
**Expected answer:** 9:30 AM to 6:00 PM IST, Monday to Friday.
**Expected source:** CONF-001 - Company Overview and Directory
**Route:** document_rag

## Q02 - What are the core collaboration hours?
**Expected answer:** 10:00 AM to 4:00 PM IST.
**Expected source:** CONF-002 - Working Hours and Attendance
**Route:** document_rag

## Q03 - How quickly must a missing attendance punch be regularized?
**Expected answer:** Within two working days.
**Expected source:** CONF-002 - Working Hours and Attendance
**Route:** document_rag

## Q04 - How many annual-leave days are provided each year?
**Expected answer:** 18 working days.
**Expected source:** CONF-003 - Leave and Holiday Policy
**Route:** document_rag

## Q05 - How many unused annual-leave days may be carried forward?
**Expected answer:** A maximum of 6 days.
**Expected source:** CONF-003 - Leave and Holiday Policy
**Route:** document_rag

## Q06 - How many days per week may an eligible employee work remotely?
**Expected answer:** Up to 3 days per week with manager approval.
**Expected source:** CONF-004 - Hybrid and Remote Work Policy
**Route:** document_rag

## Q07 - What is the reimbursement limit for an external monitor?
**Expected answer:** INR 18,000.
**Expected source:** ATT-DOCX-001 - Remote Work Equipment Standard
**Route:** document_rag

## Q08 - What approvals are required before buying remote-work equipment?
**Expected answer:** Manager approval for eligibility and budget, followed by IT Operations approval for compatibility and security, before purchase.
**Expected source:** CONF-004 and ATT-DOCX-001
**Route:** multi_source

## Q09 - How quickly must suspected phishing be reported?
**Expected answer:** Within 15 minutes.
**Expected source:** CONF-006 and Security Awareness Training video
**Route:** multi_source

## Q10 - What is the minimum password length?
**Expected answer:** 14 characters.
**Expected source:** CONF-006 - Information Security Guidelines
**Route:** document_rag

## Q11 - May Restricted information be pasted into an unapproved AI tool?
**Expected answer:** No. Restricted information must never be entered into an AI tool not approved by Information Security.
**Expected source:** CONF-006 - Information Security Guidelines
**Route:** document_rag

## Q12 - What are the four information-classification levels?
**Expected answer:** Public, Internal, Confidential, and Restricted.
**Expected source:** Security Awareness Training video - Classify Before Sharing
**Route:** video_rag

## Q13 - What should an employee do after clicking a suspected phishing link?
**Expected answer:** Report immediately, disclose that the link was clicked, follow Information Security instructions, and preserve evidence.
**Expected source:** Security Awareness Training video - Report Within 15 Minutes
**Route:** video_rag

## Q14 - What is the P1 acknowledgement target?
**Expected answer:** 15 minutes.
**Expected source:** CONF-005 and ATT-PDF-001
**Route:** multi_source

## Q15 - How often are P1 updates issued?
**Expected answer:** Every 30 minutes.
**Expected source:** ATT-PDF-001 - IT Incident Response Handbook
**Route:** document_rag

## Q16 - Who approves closure of a major incident?
**Expected answer:** The Incident Commander.
**Expected source:** ATT-PDF-001 - IT Incident Response Handbook
**Route:** document_rag

## Q17 - Within how many days must an expense claim be submitted?
**Expected answer:** Within 15 calendar days after the expense date.
**Expected source:** CONF-007 and ATT-PDF-002
**Route:** multi_source

## Q18 - What is the domestic hotel limit?
**Expected answer:** INR 6,500 per night excluding taxes.
**Expected source:** ATT-PDF-002 - Travel and Expense Quick Guide
**Route:** document_rag

## Q19 - When are three vendor quotations required?
**Expected answer:** For a purchase above INR 100,000.
**Expected source:** CONF-008 - Procurement and Vendor Onboarding
**Route:** document_rag

## Q20 - When must an S1 customer issue be escalated to the duty manager?
**Expected answer:** When it has not been assigned to a technical owner within 30 minutes.
**Expected source:** CONF-009 - Customer Support Escalation
**Route:** document_rag

## Q21 - What are the customer portal RTO and RPO?
**Expected answer:** RTO is 4 hours and RPO is 1 hour.
**Expected source:** CONF-010 - Business Continuity and Emergency Contacts
**Route:** document_rag

## Q22 - How many tickets are in the Q2 service-desk workbook?
**Expected answer:** 100 tickets.
**Expected source:** Service_Desk_Tickets_Q2_2026.xlsx - Tickets sheet
**Route:** spreadsheet_query

## Q23 - How many P1 tickets are in the workbook?
**Expected answer:** 20 P1 tickets.
**Expected source:** Service_Desk_Tickets_Q2_2026.xlsx - Tickets sheet
**Route:** spreadsheet_query

## Q24 - How many workbook tickets met their SLA target?
**Expected answer:** 39 tickets.
**Expected source:** Service_Desk_Tickets_Q2_2026.xlsx - Tickets sheet
**Route:** spreadsheet_query

## Q25 - Which team has the highest ticket volume in the workbook?
**Expected answer:** Applications (25), Infrastructure (25), Security (25), Service Desk (25).
**Expected source:** Service_Desk_Tickets_Q2_2026.xlsx - Summary sheet
**Route:** spreadsheet_query

## Q26 - How many service requests are currently open in the SQLite database?
**Expected answer:** 60 requests are open, in progress, or waiting.
**Expected source:** support_operations.db - open_service_requests view
**Route:** sql_query

## Q27 - How many open P1 requests are in the SQLite database?
**Expected answer:** 0 open P1 requests.
**Expected source:** support_operations.db - open_service_requests view
**Route:** sql_query

## Q28 - Which department submitted the most database service requests?
**Expected answer:** IT with 30 requests.
**Expected source:** support_operations.db - service_requests table
**Route:** sql_query

## Q29 - What dental insurance plan does Northstar provide?
**Expected answer:** Not enough information in the provided sources.
**Expected source:** No supporting source
**Route:** unsupported

## Q30 - What is the address of Northstar's Tokyo office?
**Expected answer:** Not enough information in the provided sources.
**Expected source:** No supporting source
**Route:** unsupported
