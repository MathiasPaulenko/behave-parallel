# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in behave-parallel, please report it
responsibly.

- Email: **mathias@paulenko.dev**
- Do not open a public GitHub issue for security vulnerabilities.

## Response time

We aim to acknowledge reported vulnerabilities within **48 hours** and to
provide a fix or mitigation according to severity.

## Scope

behave-parallel executes test code via `multiprocessing.Process`. It does not
make network calls or access the filesystem beyond reading feature files and
writing test reports. Vulnerabilities related to process isolation, pickle
deserialization of work units, or temp file handling are in scope.
