# Security policy

## Supported versions

LabHarness is pre-1.0: only the latest version on `main` receives fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Email labharness.project@gmail.com with the details and, if you can, a way to reproduce the
problem. Once the repository is public you can also use GitHub's private vulnerability reporting:
the **Security** tab, then **Report a vulnerability**. We aim to acknowledge reports within a week.

LabHarness runs locally and makes no network requests by default. The most relevant risks are
malicious input files (data, scripts or LaTeX sources) processed on your machine. Only run
workspaces you trust.
