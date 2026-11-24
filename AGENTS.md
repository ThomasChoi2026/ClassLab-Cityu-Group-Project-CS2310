# ClassLab project instructions for Codex

Before working on this repository, read `docs/PROJECT_CONTEXT.md`. Verify the current state against the actual code and the user's current request. The project background includes plans as well as implemented features.

## Project and language

- Repository: `ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310`.
- Course: City University of Hong Kong, CS2310 Computer Programming — Agentic Coding Project.
- Use English for submission materials, project documentation, interface text, and progress reports. Use English names for code and APIs.
- Teachers publish C++ programming tasks. Students join by QR code or link, edit and submit on their own devices, and receive grading results when grading is available. Teachers follow class progress live.
- The default stack is a C++20 backend with an HTML, CSS, and JavaScript frontend. Use established libraries and CMake when needed. Keep the design simple.
- The product requires no integrated AI. Coding agents can assist with development and testing. Product features should work through code, rules, and the runtime.

## Repository and Git practices

1. Work in the specified GitHub repository through the connected Codex Cloud environment. Keep project files out of the user's private CS C++ workspace on their Mac.
2. Do not access, import, copy, or upload private course slides, notebooks, recordings, exercises, archives, backups, keys, credentials, or unrelated material. If a reference is necessary, ask the user to provide the relevant portion.
3. Verify the repository identity before writing. Limit Git changes to this repository.
4. Preserve repository visibility, access permissions, and the default branch. Do not merge into `main` without authorization. Prefer a separate branch for review through a diff or pull request. Follow the user's authorization for the current task when pushing or submitting.
5. Inspect existing files and Git status first. Avoid overwriting work, duplicating files, creating empty placeholders, or claiming progress on unverified functionality.
6. Report actual changes, tests run, failures, and outstanding checks. Describe a feature as implemented only after verifying it.

## Coursework delivery

- Prioritize a reproducible GitHub checkout, a demonstrable classroom workflow, and build, test, and demo instructions for teammates and the professor.
- Use Codex Cloud for development and testing. Use a temporary private preview for recording and stop it after the demo. The Mac is for browsing.
- Public deployment, long-term operations, and commercial scaling are outside the coursework scope. Prefer free preview resources and get confirmation before creating a resource that may incur charges.

## Technical scope

- For the first version, the teacher creates a session and publishes starter code and tests. Students join by link or QR code, edit, and submit. The system reports grading status and the teacher sees participation and pass counts.
- A one-click JupyterLab publishing extension, automatic student account linking, mobile push notifications, multilingual grading, and AI tutoring are future candidates.
- Do not execute untrusted student code directly on the web server or expose execution publicly before isolation has been verified. Specify isolation, timeouts, memory, process, filesystem, and network limits. Containerization alone does not establish safety.
- A cloud workspace is temporary. To demonstrate on phones, verify the controlled preview URL and connectivity separately.

## Development order

Verify the smallest complete teacher-to-student workflow first, then add grading and progress statistics. Compile, test, and inspect actual output. Review the open questions in `docs/PROJECT_CONTEXT.md` against the repository when starting each task. Prioritize a reliable demonstration within the short coursework schedule.
