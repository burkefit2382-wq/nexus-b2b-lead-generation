# LeadGen Virtual Hub Launch QA Test Plan

This plan turns the launch checklist into evidence-driven test work. Do not mark an item complete unless there is a dated test run, command output, screenshot, report, ticket, or reviewer sign-off attached.

## Current Local Workspace Status

- Local source code was not present in this folder during setup.
- Available files only included Google AI Studio access/history exports for `LeadGen Virtual Hub`.
- No app manifest, API server, dashboard source, test suite, Docker config, or deployment URL was available locally.
- Full QA execution requires either the application repository, an exported build, or a reachable staging URL with test credentials.

## Entry Criteria

- Staging environment is deployed and matches the intended production configuration.
- Test accounts exist for every role: owner, admin, analyst, standard user, read-only user, and disabled/suspended user.
- Sample datasets are available for ingestion, OSINT enrichment, AI enrichment, and lead scoring.
- API documentation or route inventory is available.
- Logging, audit logging, and monitoring are enabled in staging.
- Test secrets are isolated from production secrets.
- Written permission is confirmed before any security scan or load test runs against hosted infrastructure.

## 1. Functional Testing

Goal: zero broken features in critical workflows.

| Area | Test | Expected Result | Evidence |
| --- | --- | --- | --- |
| Ingestion | Run each ingestion job with valid sample data | Job completes with no unhandled errors | Job log, output record count |
| Ingestion | Run jobs with malformed, empty, duplicate, and oversized input | User-safe validation error or clean rejection | Error response/log |
| OSINT | Run each OSINT module against known sample leads | Returned fields match expected sources and formats | Result comparison |
| OSINT | Test unavailable or rate-limited upstream sources | System retries or degrades without crashing | Retry log |
| AI enrichment | Run all sample datasets through enrichment | Required enrichment fields populate consistently | Before/after dataset |
| AI enrichment | Test missing/ambiguous input fields | Model output is bounded, explainable, and non-destructive | Output sample |
| Lead scoring | Run fixed dataset multiple times | Scores are deterministic or variance is documented | Score diff report |
| Dashboard | Load every dashboard view and widget | No broken components, console errors, or empty states without explanation | Browser screenshot, console log |
| API | Exercise every documented endpoint | Correct status codes, schemas, auth behavior, and errors | API test report |
| Auth | Test login, logout, session expiry, password reset, and failed login | Secure and predictable auth behavior | Auth test notes |
| Roles | Verify each role across dashboard and API | Permissions match RBAC matrix | Access matrix |

## 2. Security Testing

Goal: government-ready security posture, with documented controls and remediation.

| Area | Test | Expected Result | Evidence |
| --- | --- | --- | --- |
| Dependency scan | Run dependency vulnerability scan for frontend, backend, and containers | No critical/high unresolved vulnerabilities | Scan report |
| Static analysis | Run SAST on application code | Findings triaged and fixed or accepted | SAST report |
| SQL injection | Test parameters, filters, search, sort, auth, and ingestion inputs | Injection payloads fail safely | DAST report |
| XSS | Test reflected, stored, and DOM XSS across dashboard and forms | Payloads are encoded or rejected | Browser proof |
| CSRF | Test state-changing browser requests | CSRF protections or same-site controls block forged requests | Request trace |
| Input validation | Fuzz API and ingestion boundaries | Invalid data is rejected cleanly | Fuzz report |
| Encryption in transit | Verify HTTPS/TLS config | Strong TLS, no mixed content | TLS scan |
| Encryption at rest | Verify database, object storage, backups, and logs | Sensitive storage encrypted | Cloud/config evidence |
| API keys | Attempt missing, malformed, expired, and lower-privilege keys | Bypass is impossible | API auth test report |
| Secrets | Search repo, logs, build artifacts, and browser bundles | No secrets or tokens exposed | Secret scan |
| Logging | Trigger auth, ingestion, enrichment, and API errors | Logs contain enough audit detail without sensitive data | Redacted log samples |
| Headers | Verify security headers | CSP, HSTS, X-Content-Type-Options, frame protections where applicable | Header scan |

## 3. Performance And Load Testing

Goal: smooth performance under expected heavy usage.

| Area | Test | Target | Evidence |
| --- | --- | --- | --- |
| API latency | Baseline p50/p95/p99 for critical endpoints | Targets defined by product owner before test | Load report |
| Concurrent users | Simulate 50, 100, and 200 users | No error spike or unacceptable latency | Load report |
| Ingestion scale | Run large datasets at realistic and peak size | Completes within target window | Job metrics |
| Long jobs | Run enrichment and ingestion jobs for extended duration | No memory leak, timeout, or stuck job | Metrics graph |
| Database | Stress common queries and write-heavy paths | Indexes and connection pools hold steady | DB metrics |
| AI latency | Benchmark enrichment model latency and timeout handling | Latency budget documented and met | Model timing report |
| Backpressure | Exceed queue or rate limits intentionally | System throttles cleanly | Queue metrics |

## 4. Reliability And Failover Testing

Goal: services recover automatically and jobs remain consistent.

| Area | Test | Expected Result | Evidence |
| --- | --- | --- | --- |
| Service restart | Restart services during active ingestion | Job resumes or fails safely with retry | Job state log |
| Worker failure | Kill worker during enrichment | Job is re-queued or recoverable | Queue/job log |
| Network interruption | Simulate upstream timeout and dropped connection | Retry policy works and avoids duplicate writes | Trace/log |
| Database interruption | Temporarily block database connection in staging | App fails gracefully and recovers | Metrics/log |
| Job persistence | Restart system with queued jobs | Pending/running jobs are not lost | Queue inspection |
| Idempotency | Retry ingestion/enrichment after partial failure | No duplicate records or corrupted scores | Data diff |

## 5. Compliance Readiness

Goal: produce the policies and controls government buyers expect to review.

| Control | Required Artifact |
| --- | --- |
| Data retention | Written retention and deletion policy |
| Access control | RBAC matrix and admin process |
| Audit logging | Audit event list and sample audit export |
| Encryption | Encryption policy for data at rest and in transit |
| Privacy | Privacy policy and data handling statement |
| Incident response | Incident response plan with severity levels and contacts |
| Vendor/security | Dependency and vendor risk notes |
| Rate limiting | API rate-limit policy and abuse handling |
| Backup/recovery | Backup frequency, restore test evidence, RPO/RTO targets |
| Change management | Release checklist and approval flow |

## 6. UX And Onboarding Testing

Goal: users can begin work without confusion or dead ends.

| Area | Test | Expected Result | Evidence |
| --- | --- | --- | --- |
| Sign-up | Complete sign-up with valid, invalid, duplicate, and invited users | Clear success/failure states | Screen recording |
| Onboarding | Complete first-run checklist for every role | Each role sees relevant steps only | UX notes |
| Demo mode | Start and exit demo mode | Demo data is isolated and resettable | Screenshot |
| Tooltips | Review all tooltips and walkthrough steps | Helpful, accurate, non-blocking | QA notes |
| Docs | Follow docs as a new user | Tasks can be completed without internal knowledge | Tester notes |
| Error messages | Trigger common errors | Messages are actionable and do not leak internals | Error samples |
| Accessibility | Keyboard navigation and screen-reader pass on core flows | No critical blockers | Accessibility report |

## 7. Pilot Testing

Goal: validate the product with real users before public launch.

- Recruit 3 to 10 trusted testers.
- Give each tester realistic tasks:
  - Import a lead dataset.
  - Run OSINT enrichment.
  - Review AI-enriched fields.
  - Filter and score leads.
  - Export or act on a prioritized lead list.
  - Invite a teammate with a different role.
- Collect:
  - Time to complete each task.
  - Confusing steps.
  - Bugs or inconsistent results.
  - Missing data or trust concerns.
  - Performance complaints.
- Fix critical and high issues before launch.

## 8. Final QA Pass

Goal: launch only after critical paths remain clean after fixes.

- Re-test functional critical paths.
- Re-test security findings marked fixed.
- Re-test load and performance targets.
- Re-test onboarding and documentation.
- Re-test billing, if enabled.
- Re-test dashboard and API smoke tests.
- Confirm no critical/high open defects remain.
- Confirm rollback plan exists.
- Confirm monitoring and alerting are active.

## Exit Criteria

- All critical functional workflows pass.
- No unresolved critical or high security vulnerabilities remain.
- Performance targets are met for agreed traffic levels.
- Reliability tests prove jobs recover or fail safely.
- Required compliance artifacts are complete enough for buyer review.
- Pilot feedback has been triaged and launch-blocking issues are fixed.
- Final QA sign-off is recorded with date, environment, version, and approver.

