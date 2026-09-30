# Requirements Document

## Introduction

CampusHire AI is an AI-powered placement readiness and skill-gap analyzer for college students, submitted for Kiro University 2026 as a real, runnable web application. A student builds a profile (skills, certifications, academic projects, resume) and supplies a target job description. The system extracts the skills required by the target job, compares them against the student's declared and resume-derived skills, computes a transparent and deterministic placement-readiness score from 0 to 100, identifies missing or weak skills, and produces a prioritized learning roadmap. Results are presented through a clean web dashboard.

The system is delivered as a React + TypeScript frontend communicating over a REST API with a Python + FastAPI backend, persisting data in SQLite, packaged with Docker, and validated with pytest and property-based tests. The scoring logic is the correctness-critical core of the product: it MUST be transparent (every point traceable to a contributing factor) and deterministic (identical inputs always produce identical scores), because it is validated with property-based testing.

This document defines the product overview, personas, user stories, functional and non-functional requirements, and measurable acceptance criteria in EARS format.

## Product Overview

- **Purpose**: Help college students objectively measure how prepared they are for a specific target job and give them an actionable, prioritized plan to close the gaps.
- **Primary outcome**: A transparent 0-100 placement-readiness score, a categorized skill-gap report, and a prioritized learning roadmap, all viewable on a web dashboard.
- **Scope of this spec**: Profile management, skill/certification/project management, resume ingestion, job-description skill extraction, skill comparison, deterministic scoring, gap identification, roadmap generation, and dashboard presentation over a REST API.
- **Out of scope for this spec**: Authentication providers, payment, multi-tenant administration, and live job-board integrations (may be addressed in later specs).

## User Personas

- **Student (Primary User)**: An undergraduate preparing for campus placements. Wants to know readiness for a specific role and what to learn next. Technical familiarity varies; needs clear, non-jargon output.
- **Placement Coordinator (Secondary User)**: A college staff member who reviews student readiness. Wants transparent, explainable scores they can trust and communicate. In this spec, interacts only as a viewer of a student's generated results.
- **Evaluator/Judge (Kiro University 2026)**: Assesses whether the application is real, runnable, and demonstrates spec-driven development, steering, hooks, property-based testing, Powers, MCP, and custom agents. Needs reproducible behavior and verifiable determinism.

## Glossary

- **System**: The CampusHire AI application as a whole (frontend, backend, and database).
- **API**: The FastAPI REST backend exposing endpoints consumed by the frontend.
- **Dashboard**: The React + TypeScript web frontend that displays profile data and analysis results.
- **Student_Profile**: A persisted record identifying a student and owning their skills, certifications, projects, and resume.
- **Technical_Skill**: A named competency of a technical nature (e.g., "Python", "SQL") associated with a Student_Profile, with an optional proficiency level.
- **Soft_Skill**: A named non-technical competency (e.g., "Communication", "Teamwork") associated with a Student_Profile, with an optional proficiency level.
- **Certification**: A named credential (e.g., "AWS Certified Cloud Practitioner") associated with a Student_Profile.
- **Academic_Project**: A named project entry with a description associated with a Student_Profile.
- **Resume**: Free-form text submitted by upload or paste, attributed to a Student_Profile, from which skills may be derived.
- **Job_Description**: Free-form text describing a target role, submitted by the student for analysis.
- **Skill_Extractor**: The backend component that identifies a set of required skills from a Job_Description and derived skills from a Resume.
- **Required_Skill**: A skill identified by the Skill_Extractor as needed by the target Job_Description, optionally weighted by importance.
- **Skill_Comparator**: The backend component that compares the student's skill set against the Required_Skill set.
- **Proficiency_Level**: An ordinal measure of competency in a skill on a fixed scale from 1 (Beginner) to 5 (Expert).
- **Matched_Skill**: A Required_Skill for which the student has a corresponding skill at or above a defined proficiency threshold.
- **Weak_Skill**: A Required_Skill for which the student has a corresponding skill below the defined proficiency threshold.
- **Missing_Skill**: A Required_Skill for which the student has no corresponding skill.
- **Scoring_Engine**: The backend component that computes the Readiness_Score.
- **Readiness_Score**: An integer from 0 to 100 representing placement readiness for a target Job_Description.
- **Score_Breakdown**: The itemized set of contributing factors, weights, and point contributions that sum to the Readiness_Score.
- **Roadmap_Generator**: The backend component that produces the prioritized Learning_Roadmap.
- **Learning_Roadmap**: An ordered list of learning items addressing Missing_Skill and Weak_Skill entries, ordered by priority.
- **Analysis**: A persisted result set for one Student_Profile and one Job_Description, containing the Score_Breakdown, gap categorization, and Learning_Roadmap.

## Requirements

### Requirement 1: Student Profile Management

**User Story:** As a student, I want to create and manage a student profile, so that all my placement data is organized under one identity.

#### Acceptance Criteria

1. WHEN a student submits a create-profile request containing a non-empty name, THE API SHALL create a Student_Profile, assign a unique identifier, and return the identifier.
2. IF a create-profile request contains an empty or whitespace-only name, THEN THE API SHALL reject the request with a validation error and SHALL NOT create a Student_Profile.
3. WHEN a student requests a Student_Profile by its identifier, THE API SHALL return the Student_Profile including its skills, certifications, and projects.
4. WHEN a student issues a get-profile-by-identifier request for a Student_Profile identifier that does not exist, THE API SHALL return a not-found error.
5. WHEN a student updates an existing Student_Profile with a non-empty name, THE API SHALL persist the change and return the updated Student_Profile.
6. THE Dashboard SHALL display the active Student_Profile name and identifier on the profile view.

### Requirement 2: Technical and Soft Skills Management

**User Story:** As a student, I want to add technical skills and soft skills with proficiency levels, so that my competencies are represented for comparison.

#### Acceptance Criteria

1. WHEN a student adds a Technical_Skill with a non-empty name to a Student_Profile, THE API SHALL persist the Technical_Skill associated with that Student_Profile and return the stored record.
2. WHEN a student adds a Soft_Skill with a non-empty name to a Student_Profile, THE API SHALL persist the Soft_Skill associated with that Student_Profile and return the stored record.
3. WHERE a student provides a Proficiency_Level for a skill, THE API SHALL accept the value only if it is an integer from 1 to 5 inclusive.
4. IF a student provides a Proficiency_Level outside the range 1 to 5, THEN THE API SHALL reject the request with a validation error and SHALL NOT persist the skill.
5. WHERE a student adds a skill without a Proficiency_Level, THE API SHALL assign a default Proficiency_Level of 1.
6. IF a student adds a skill whose name duplicates an existing skill of the same type on the same Student_Profile (case-insensitive), THEN THE API SHALL reject the request with a conflict error and SHALL NOT create a duplicate.
7. WHEN a student removes a skill from a Student_Profile, THE API SHALL delete the skill association and return a success confirmation.
8. THE Dashboard SHALL display technical skills and soft skills as separate labeled groups.

### Requirement 3: Certifications Management

**User Story:** As a student, I want to add certifications, so that my verified credentials contribute to my readiness.

#### Acceptance Criteria

1. WHEN a student adds a Certification with a non-empty name to a Student_Profile, THE API SHALL persist the Certification associated with that Student_Profile and return the stored record.
2. IF a student adds a Certification with an empty or whitespace-only name, THEN THE API SHALL reject the request with a validation error and SHALL NOT persist the Certification.
3. WHEN a student removes a Certification from a Student_Profile, THE API SHALL delete the Certification and return a success confirmation.
4. THE Dashboard SHALL display the list of certifications associated with the active Student_Profile.
5. WHEN the active Student_Profile changes, THE Dashboard SHALL re-fetch and display the certification list for the newly active Student_Profile.

### Requirement 4: Academic Projects Management

**User Story:** As a student, I want to add academic projects with descriptions, so that my practical experience is represented.

#### Acceptance Criteria

1. WHEN a student adds an Academic_Project with a non-empty title to a Student_Profile, THE API SHALL persist the Academic_Project associated with that Student_Profile and return the stored record.
2. IF a student adds an Academic_Project with an empty or whitespace-only title, THEN THE API SHALL reject the request with a validation error and SHALL NOT persist the Academic_Project.
3. WHERE a student provides a project description, THE API SHALL store the description with the Academic_Project.
4. WHEN a student removes an Academic_Project from a Student_Profile, THE API SHALL delete the Academic_Project and return a success confirmation.
5. THE Dashboard SHALL display the list of academic projects with their titles and descriptions.

### Requirement 5: Resume Ingestion

**User Story:** As a student, I want to upload or paste my resume, so that skills stated in my resume can inform the analysis.

#### Acceptance Criteria

1. WHEN a student submits Resume text by paste for a Student_Profile, THE API SHALL store the Resume text associated with that Student_Profile and return a success confirmation.
2. WHEN a student uploads a plain-text or PDF resume file for a Student_Profile, THE API SHALL extract the text content and store it as the Resume text for that Student_Profile.
3. IF a student submits a Resume with empty content, THEN THE API SHALL reject the request with a validation error and SHALL NOT store the Resume.
4. IF a student uploads a resume file whose type is not plain text or PDF, THEN THE API SHALL reject the request with an unsupported-media error and SHALL NOT store the Resume.
5. IF a student uploads a resume file larger than 5 megabytes, THEN THE API SHALL reject the request with a payload-too-large error and SHALL NOT store the Resume.
6. WHEN a student submits a new Resume for a Student_Profile that already has a Resume, THE API SHALL replace the previously stored Resume text.

### Requirement 6: Target Job Description Entry

**User Story:** As a student, I want to enter a target job description, so that the analysis is tailored to a specific role.

#### Acceptance Criteria

1. WHEN a student submits a Job_Description with non-empty text for a Student_Profile, THE API SHALL accept the Job_Description and associate it with the requested Analysis.
2. IF a student submits a Job_Description with empty or whitespace-only text, THEN THE API SHALL reject the request with a validation error and SHALL NOT start an Analysis.
3. IF a student submits a Job_Description exceeding 20000 characters, THEN THE API SHALL reject the request with a validation error and SHALL NOT start an Analysis.
4. THE Dashboard SHALL provide an input area for entering the target Job_Description text.

### Requirement 7: Required-Skill Extraction from Job Description

**User Story:** As a student, I want the system to identify the skills required by the target job, so that I know what the role demands.

#### Acceptance Criteria

1. WHEN a valid Job_Description is analyzed, THE Skill_Extractor SHALL produce a set of Required_Skill entries derived from the Job_Description.
2. WHERE the Skill_Extractor assigns an importance weight to a Required_Skill, THE Skill_Extractor SHALL express the weight as a value from 1 to 5 inclusive.
3. THE Skill_Extractor SHALL produce a Required_Skill set containing no duplicate skill names when compared case-insensitively.
4. THE Skill_Extractor SHALL normalize each Required_Skill name by trimming leading and trailing whitespace and collapsing internal whitespace runs to a single space before de-duplication.
5. WHEN the same Job_Description text is analyzed more than once, THE Skill_Extractor SHALL produce an identical Required_Skill set with identical weights (deterministic extraction).
6. IF a Job_Description yields zero Required_Skill entries, THEN THE API SHALL return an Analysis indicating that no required skills were identified and SHALL set the Readiness_Score to 0.

### Requirement 8: Skill Comparison and Gap Categorization

**User Story:** As a student, I want my skills compared against the job requirements, so that I can see exactly where I match and where I fall short.

#### Acceptance Criteria

1. WHEN an Analysis runs, THE Skill_Comparator SHALL compare the union of the student's declared skills and Resume-derived skills against the Required_Skill set using case-insensitive name matching.
2. WHEN a Required_Skill matches a student skill whose Proficiency_Level is greater than or equal to 3, THE Skill_Comparator SHALL categorize the Required_Skill as a Matched_Skill.
3. WHEN a Required_Skill matches a student skill whose Proficiency_Level is less than 3, THE Skill_Comparator SHALL categorize the Required_Skill as a Weak_Skill.
4. WHEN a Required_Skill has no matching student skill, THE Skill_Comparator SHALL categorize the Required_Skill as a Missing_Skill.
5. THE Skill_Comparator SHALL assign each Required_Skill to exactly one of the categories Matched_Skill, Weak_Skill, or Missing_Skill.
6. THE Skill_Comparator SHALL ensure the count of Matched_Skill, Weak_Skill, and Missing_Skill entries sums to the total count of Required_Skill entries.

### Requirement 9: Skill Comparison Determinism and Invariance

**User Story:** As an evaluator, I want the comparison to be deterministic and independent of input ordering, so that results are trustworthy and reproducible.

#### Acceptance Criteria

1. WHEN the same student skill set and the same Required_Skill set are compared more than once, THE Skill_Comparator SHALL produce identical categorization results (deterministic comparison).
2. WHEN the order of the student skill list is changed without changing its contents, THE Skill_Comparator SHALL produce identical categorization results (order invariance).
3. WHEN the order of the Required_Skill list is changed without changing its contents, THE Skill_Comparator SHALL produce identical categorization results (order invariance).

### Requirement 10: Transparent and Deterministic Readiness Score

**User Story:** As a student, I want a transparent placement-readiness score from 0 to 100, so that I can trust the number and understand how it was derived.

#### Acceptance Criteria

1. WHEN an Analysis runs, THE Scoring_Engine SHALL compute a Readiness_Score that is an integer from 0 to 100 inclusive.
2. WHEN the same student skill set, Required_Skill set with weights, and categorization are provided more than once, THE Scoring_Engine SHALL produce an identical Readiness_Score (determinism).
3. WHEN the Scoring_Engine computes a Readiness_Score, THE Scoring_Engine SHALL produce a Score_Breakdown in which the sum of all itemized point contributions equals the Readiness_Score (transparency and conservation).
4. WHERE weighted point allocations do not divide into whole integers that sum exactly to the Readiness_Score, THE Scoring_Engine SHALL distribute the rounding remainder to the highest-weighted Required_Skill contributions first using a deterministic largest-remainder rule, breaking ties alphabetically by skill name.
5. WHERE every Required_Skill is categorized as a Matched_Skill, THE Scoring_Engine SHALL compute a Readiness_Score of 100.
6. WHERE every Required_Skill is categorized as a Missing_Skill, THE Scoring_Engine SHALL compute a Readiness_Score of 0.
7. WHEN a Matched_Skill in one Analysis is changed to a Weak_Skill or Missing_Skill for the same Required_Skill set and weights, THE Scoring_Engine SHALL compute a Readiness_Score that is less than or equal to the original Readiness_Score (monotonicity).
8. WHEN a Weak_Skill in one Analysis is changed to a Matched_Skill for the same Required_Skill set and weights, THE Scoring_Engine SHALL compute a Readiness_Score that is greater than or equal to the original Readiness_Score (monotonicity).
9. THE Scoring_Engine SHALL contribute points for a Weak_Skill that are greater than or equal to the points contributed for a Missing_Skill of equal weight, and less than or equal to the points contributed for a Matched_Skill of equal weight.
10. THE Score_Breakdown SHALL identify, for each Required_Skill, the skill name, its weight, its category, and its point contribution.
11. WHEN the Skill_Extractor assigns non-negative importance weights to Required_Skill entries, THE Scoring_Engine SHALL weight each Required_Skill's contribution in proportion to its assigned weight relative to the sum of all Required_Skill weights.
12. IF the Required_Skill set is empty, THEN THE Scoring_Engine SHALL compute a Readiness_Score of 0 and produce an empty Score_Breakdown.
13. IF the sum of all Required_Skill weights is 0, THEN THE Scoring_Engine SHALL allocate points equally across Required_Skill entries using the same deterministic largest-remainder rule defined in Acceptance Criterion 4.

### Requirement 11: Missing and Weak Skill Identification

**User Story:** As a student, I want the system to identify my missing or weak skills, so that I know precisely what to improve.

#### Acceptance Criteria

1. WHEN an Analysis completes, THE API SHALL return the list of Missing_Skill entries with their names and weights.
2. WHEN an Analysis completes, THE API SHALL return the list of Weak_Skill entries with their names, weights, and current Proficiency_Level.
3. THE Dashboard SHALL display Missing_Skill and Weak_Skill entries as distinct, labeled groups.

### Requirement 12: Prioritized Learning Roadmap

**User Story:** As a student, I want a prioritized learning roadmap, so that I can address the most impactful gaps first.

#### Acceptance Criteria

1. WHEN an Analysis completes, THE Roadmap_Generator SHALL produce a Learning_Roadmap containing one learning item for each Missing_Skill and each Weak_Skill.
2. THE Roadmap_Generator SHALL order Learning_Roadmap items in descending order of Required_Skill weight.
3. WHERE two Learning_Roadmap items have equal Required_Skill weight, THE Roadmap_Generator SHALL order a Missing_Skill item before a Weak_Skill item.
4. WHERE two Learning_Roadmap items have equal weight and equal category, THE Roadmap_Generator SHALL order them alphabetically by skill name to ensure a deterministic order.
5. WHEN the same set of Missing_Skill and Weak_Skill entries is provided more than once, THE Roadmap_Generator SHALL produce an identically ordered Learning_Roadmap (determinism).
6. THE Roadmap_Generator SHALL exclude Matched_Skill entries from the Learning_Roadmap.
7. THE Dashboard SHALL display the Learning_Roadmap as an ordered list reflecting priority.

### Requirement 13: Analysis Persistence and Retrieval

**User Story:** As a student, I want my analysis results saved, so that I can revisit my readiness without re-running the analysis.

#### Acceptance Criteria

1. WHEN an Analysis completes successfully, THE API SHALL persist the Analysis including its Readiness_Score, Score_Breakdown, gap categorization, and Learning_Roadmap.
2. WHEN a student requests a persisted Analysis by its identifier, THE API SHALL return the stored Analysis.
3. IF a student requests an Analysis identifier that does not exist, THEN THE API SHALL return a not-found error.
4. WHEN a student requests the list of analyses for a Student_Profile, THE API SHALL return all persisted analyses associated with that Student_Profile.

### Requirement 14: Web Dashboard Presentation

**User Story:** As a student, I want a clean web dashboard, so that I can view my profile and analysis results clearly.

#### Acceptance Criteria

1. WHEN a student opens the Dashboard, THE Dashboard SHALL present navigation to the profile view and the analysis view.
2. WHEN an Analysis result is available, THE Dashboard SHALL display the Readiness_Score, the Score_Breakdown, the gap categorization, and the Learning_Roadmap on a single results view.
3. WHILE an Analysis request is in progress, THE Dashboard SHALL display an in-progress indicator.
4. IF the API returns an error for a Dashboard request, THEN THE Dashboard SHALL display a human-readable error message describing the failure.
5. THE Dashboard SHALL communicate with the backend exclusively through the REST API.

### Requirement 15: REST API and Data Contract

**User Story:** As a frontend developer, I want a well-defined REST API, so that the Dashboard can integrate reliably with the backend.

#### Acceptance Criteria

1. THE API SHALL expose REST endpoints for Student_Profile, skills, certifications, projects, resume, and analysis operations.
2. WHEN the API receives a request whose body fails schema validation, THE API SHALL return a validation error with a status code of 422 and a descriptive message.
3. WHEN the API responds to a request, THE API SHALL return responses encoded as JSON.
4. THE API SHALL return a status code of 200 or 201 for successful operations, 400 or 422 for client validation errors, 404 for missing resources, and 409 for conflicts.
5. IF a request simultaneously satisfies a missing-resource condition and a conflict condition, THEN THE API SHALL return a status code of 404, giving the missing-resource condition precedence over the conflict condition.
6. THE API SHALL expose a health-check endpoint that returns a success status when the service is operational.

### Requirement 16: Data Persistence

**User Story:** As a student, I want my data stored reliably, so that my profile and analyses persist across sessions.

#### Acceptance Criteria

1. THE System SHALL persist Student_Profile, Technical_Skill, Soft_Skill, Certification, Academic_Project, Resume, and Analysis records in a SQLite database.
2. WHEN the System restarts, THE API SHALL return previously persisted records unchanged.
3. WHEN a Student_Profile is deleted, THE API SHALL delete all skills, certifications, projects, resume, and analyses associated with that Student_Profile.

## Non-Functional Requirements

### Requirement 17: Performance

**User Story:** As a student, I want fast responses, so that I can iterate on my profile and analysis quickly.

#### Acceptance Criteria

1. WHEN the API receives an analysis request for a Job_Description of up to 20000 characters and a Student_Profile of up to 200 skills, THE API SHALL return the Analysis within 3 seconds under a single-user load on the reference environment.
2. WHEN the API receives a profile read request, THE API SHALL return the response within 500 milliseconds under a single-user load on the reference environment.

### Requirement 18: Reliability and Error Handling

**User Story:** As a student, I want the system to handle errors gracefully, so that failures are understandable and recoverable.

#### Acceptance Criteria

1. IF the API encounters an unexpected internal error, THEN THE API SHALL return a status code of 500 with a generic message that excludes internal stack traces and excludes field-level detail.
2. WHEN the API rejects a request due to validation failure, THE API SHALL return a message identifying which field or condition failed validation.

### Requirement 19: Portability and Deployment

**User Story:** As an evaluator, I want the application to be runnable in a container, so that I can reproduce results reliably.

#### Acceptance Criteria

1. THE System SHALL provide a Docker configuration that builds and runs the frontend and backend.
2. WHEN the containerized System is started per the provided instructions, THE System SHALL expose the Dashboard and the API without additional manual code changes.
3. THE System SHALL run with the SQLite database persisted to a mounted volume so that data survives container restarts.

### Requirement 20: Testability and Quality Assurance

**User Story:** As an evaluator, I want the correctness-critical logic validated by property-based testing, so that determinism and transparency are proven, not merely asserted.

#### Acceptance Criteria

1. THE System SHALL include pytest-based tests covering the Skill_Extractor, Skill_Comparator, Scoring_Engine, and Roadmap_Generator.
2. THE System SHALL include property-based tests asserting the determinism of the Scoring_Engine as defined in Requirement 10 Acceptance Criterion 2.
3. THE System SHALL include property-based tests asserting the score-conservation property of the Score_Breakdown as defined in Requirement 10 Acceptance Criterion 3.
4. THE System SHALL include property-based tests asserting the bounds property that the Readiness_Score remains within 0 to 100 inclusive as defined in Requirement 10 Acceptance Criterion 1.
5. THE System SHALL include property-based tests asserting the monotonicity properties defined in Requirement 10 Acceptance Criteria 7 and 8.
6. THE System SHALL include property-based tests asserting the order-invariance properties of the Skill_Comparator defined in Requirement 9.
7. THE System SHALL include property-based tests asserting the deterministic ordering of the Learning_Roadmap defined in Requirement 12 Acceptance Criterion 5.

### Requirement 21: Maintainability and Kiro Artifacts

**User Story:** As an evaluator, I want the project to demonstrate spec-driven development and Kiro tooling, so that the submission meets Kiro University 2026 criteria.

#### Acceptance Criteria

1. THE System SHALL include steering documents describing project conventions and guidance.
2. THE System SHALL include at least one hook that automates a development or quality task.
3. THE System SHALL include configuration demonstrating use of a Power and an MCP integration.
4. THE System SHALL include at least one custom agent configuration relevant to the project workflow.
5. THE System SHALL be derived from this spec such that requirements, design, and tasks documents exist under the spec directory.

### Requirement 22: Usability and Accessibility

**User Story:** As a student, I want the dashboard to be clear and accessible, so that I can use it comfortably.

#### Acceptance Criteria

1. THE Dashboard SHALL label all form inputs with visible, associated labels.
2. THE Dashboard SHALL present the Readiness_Score together with its numeric value and the Score_Breakdown that explains it.
3. WHEN a Dashboard action fails validation, THE Dashboard SHALL display the validation message adjacent to the relevant input.

### Requirement 23: Security and Privacy

**User Story:** As a student, I want my data handled safely, so that my information is protected.

#### Acceptance Criteria

1. WHEN the API processes request input, THE API SHALL validate and sanitize input before persistence to prevent injection.
2. THE API SHALL use parameterized database operations for all SQLite queries.
3. IF a request references a Student_Profile identifier that does not exist, THEN THE API SHALL return a not-found error without disclosing internal storage details.
