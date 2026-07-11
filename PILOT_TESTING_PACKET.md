# LeadGen Virtual Hub Pilot Testing Packet

Use this packet for a controlled pilot with 3 to 10 trusted testers before public launch.

## Pilot Goal

Validate that real users can import leads, enrich them, score them, review results, and take action without support intervention.

## Tester Profile

Recruit testers who match likely buyers or users:

- Founder or sales operator.
- Business development user.
- Analyst or researcher.
- Admin or operations manager.
- Security-conscious reviewer, if selling to regulated or government-facing customers.

## Pilot Rules

- Use staging or a private pilot environment.
- Do not use production customer data unless legal, security, and privacy controls are already approved.
- Tell testers what data is safe to upload.
- Give testers realistic tasks, not a tour.
- Collect both qualitative feedback and timing/error evidence.
- Fix critical issues before expanding the pilot.

## Tester Task Script

Give each tester these tasks and ask them to narrate confusion, hesitation, and trust concerns.

| Task | Success Criteria | Tester Notes |
| --- | --- | --- |
| Create account or accept invite | Tester reaches dashboard without help | |
| Complete onboarding | Tester understands what to do first | |
| Import a sample lead dataset | Import completes and record count is clear | |
| Run OSINT enrichment | Tester can tell where data came from | |
| Run AI enrichment | Enriched fields are useful and explainable | |
| Review lead scoring | Tester understands high/medium/low priority | |
| Filter leads | Tester can find the best leads quickly | |
| Export or save a lead list | Output matches selected filters | |
| Invite another user | Role and permissions are understandable | |
| Recover from an error | Error message is clear and not scary | |

## Metrics To Capture

| Metric | Target |
| --- | --- |
| Time to first successful import | TBD |
| Time to first enriched lead list | TBD |
| Onboarding completion rate | 90% or higher for pilot |
| Critical task success rate | 90% or higher for pilot |
| Support-needed moments per tester | 1 or fewer |
| Tester confidence score | 4 out of 5 or higher |
| Critical/high bugs | 0 open before launch |

## Feedback Questions

Ask each tester:

1. What were you trying to accomplish?
2. Where did you hesitate?
3. Which output did you trust most?
4. Which output did you trust least?
5. Did any data feel missing, wrong, or unexplained?
6. Did the lead score match your intuition?
7. What would stop you from paying for this?
8. What would make you recommend it?
9. What should be removed, simplified, or renamed?
10. What one thing must be fixed before launch?

## Bug Triage

| Severity | Definition | Launch Rule |
| --- | --- | --- |
| Critical | Data loss, auth/RBAC failure, security leak, payment error, system unavailable | Must fix before launch |
| High | Core workflow broken or misleading output likely to damage trust | Must fix or formally defer with limited launch |
| Medium | Important workflow friction with workaround | Triage before launch |
| Low | Cosmetic, copy, minor polish | Can defer |

## Pilot Exit Criteria

- At least 3 testers complete the full task script.
- No critical issues remain.
- High issues are fixed or explicitly accepted for limited launch.
- Onboarding and first-value workflow are clear.
- Enrichment and scoring outputs are trusted enough for real use.
- Product owner signs off on the next launch stage.

