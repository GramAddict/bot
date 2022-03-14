# Contributing to GramAddict

:+1::tada: First off, thanks for taking the time to contribute! :tada::+1:

The following is a set of guidelines for contributing to GramAddict and its associated repos, which are hosted in the [GramAddict Organization](https://github.com/gramaddict) on GitHub. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

#### Table Of Contents
- [I don't want to read this whole thing, I just have a question!!!](#i-dont-want-to-read-this-whole-thing-i-just-have-a-question)
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
  - [Pull Requests](#pull-requests)
- [Styleguides](#styleguides)
  - [Git Commit Messages](#git-commit-messages)
  - [Python Styleguide](#javascript-styleguide)

<br />

## I don't want to read this whole thing I just have a question!!!

> **Note:** Please don't file an issue to ask a question. You may not get any assistance and if you do get any, you would have gotten faster results by using the resources below.


We have a detailed FAQ and docs website where you can learn how to use GramAddict: [https://docs.gramaddict.org/](https://docs.gramaddict.org/)


If you can't find the answer or want to chat with other people using GramAddict; you can join the official GramAddict discord server. Here there are many active members of the community - as well as the development team -  who chime in with helpful advice if you have questions.

  - [Discord Server](https://discord.com/channels/771481743471017994) - If you've never joined before, use the [Invite Link](https://discord.com/invite/NK8PNEFGFF)
    > **Note:** Even though Discord is a chat service, sometimes it takes several hours for community members to respond &mdash; please be patient!
    - Use the `#general` channel for general questions or discussion about GramAddict
    - Use the `#community-support` channel for help with issues or questions about running the bot
    - Use the `#development` channel for questions or discussion about writing or contributing to GramAddict packages
    - Use the `#lobby` channel for creating a ticket to share a crash report
    - There are other channels available as well, check the channel list

<br />

## Code of Conduct

This project and everyone participating in it is governed by the [GramAddict Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior via the [Discord Server](https://discord.com/invite/NK8PNEFGFF). Please direct them to any of the project owners via DM.

<br />

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for GramAddict. Following these guidelines helps maintainers and the community understand your report :pencil:, reproduce the behavior :computer: :computer:, and find related reports :mag_right:.

Before creating bug reports, please check [this list](#before-submitting-a-bug-report) as you might find out that you don't need to create one. When you are creating a bug report, please [include as many details as possible](#how-do-i-submit-a-good-bug-report). Fill out [the required template](https://github.com/gramaddict/bot/blob/master/.github/ISSUE_TEMPLATE/bug_report.md), the information it asks for helps us resolve issues faster.

> **Note:** If you find a **Closed** issue that seems like it is the same thing that you're experiencing, open a new issue and include a link to the original issue in the body of your new one.

#### Before Submitting A Bug Report

* **Check the [docs](https://docs.gramaddict.org).** You might be able to find the cause of the problem and fix things yourself. Most importantly, check if you can reproduce the problem [in the latest version of GramAddict](https://github.com/GramAddict/bot/releases/latest).
* **Check the [FAQs on the docs site](https://docs.gramaddict.org/#/?id=faq)** for a list of common questions and problems.
* **Perform a [cursory search](https://github.com/search?q=+is%3Aissue+user%3Agramaddict)** to see if the problem has already been reported. If it has **and the issue is still open**, add a comment to the existing issue instead of opening a new one.

#### How Do I Submit A (Good) Bug Report?

Bugs are tracked as [GitHub issues](https://guides.github.com/features/issues/). After you've determined [you have a valid bug report](#before-submitting-a-bug-report) and there is not an existing issue open for it; create an issue on the associated repository and provide the following information by filling in [the template](https://github.com/gramaddict/bot/blob/master/.github/ISSUE_TEMPLATE/bug_report.md).

Explain the problem and include additional details to help maintainers reproduce the problem:

* **Use a clear and descriptive title** for the issue to identify the problem.
* **Describe the exact steps which reproduce the problem** in as many details as possible. For example, start by explaining how you started GramAddict, e.g. which command exactly you used in the terminal, or how you started GramAddict otherwise. When listing steps, **don't just say what you did, but explain how you did it**. For example, provide the arguments you ran it with.
* **Provide specific examples to demonstrate the steps**. Include links to files or GitHub projects, or copy/pasteable snippets, which you use in those examples. If you're providing snippets in the issue, use [Markdown code blocks](https://help.github.com/articles/markdown-basics/#multiple-lines).
* **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
* **Explain which behavior you expected to see instead and why.**
* **If you're reporting that GramAddict crashed**, please open a ticket on discord, upload the crash file there, and then provide the ticket number in the issue.
* **If the problem wasn't triggered by a specific action**, describe what you were doing before the problem happened and share more information using the guidelines below.
* **Specify the name and version of the OS you're using.**
* **Specify the model of phone/tablet or name and version number of the emulator you are using.**
* **Specify the version of Instagram you are running.**

Provide more context by answering these questions:

* **Can you reproduce the problem in every time** or was it a temporary issue with another open dialogue on your device?
* **Did the problem start happening recently** (e.g. after updating to a new version of GramAddict) or was this always a problem?
* If the problem started happening recently, **can you reproduce the problem in an older version of GramAddict?** What's the most recent version in which the problem doesn't happen? You can download older versions of GramAddict from [the releases page](https://github.com/gramaddict/bot/releases)

Include details about your configuration and environment:

* **Which version of GramAddict are you using?** You can get the exact version by checking the log when you run the script.
* **What's the name and version of the OS you're using**?

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for GramAddict, including completely new features and minor improvements to existing functionality. Following these guidelines helps maintainers and the community understand your suggestion :pencil: and find related suggestions :mag_right:.

Before creating enhancement suggestions, please check [this list](#before-submitting-an-enhancement-suggestion) as you might find out that you don't need to create one. When you are creating an enhancement suggestion, please [include as many details as possible](#how-do-i-submit-a-good-enhancement-suggestion). Fill in [the template](https://github.com/gramaddict/bot/blob/master/.github/ISSUE_TEMPLATE/feature_request.md), including the steps that you imagine you would take if the feature you're requesting existed.

#### Before Submitting An Enhancement Suggestion

* **Check the [docs](https://doc.gramaddict.org).**  for tips — you might discover that the enhancement is already available. Most importantly, check if you're using [in the latest version of GramAddict](https://github.com/GramAddict/bot/releases/latest).
* **Perform a [cursory search](https://github.com/search?q=+is%3Aissue+user%3Agramaddict)** to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.

#### How Do I Submit A (Good) Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub issues](https://guides.github.com/features/issues/). After you've determined your enhancement suggestion is valid, create an issue on the associated repository and provide the following information:

* **Use a clear and descriptive title** for the issue to identify the suggestion.
* **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
* **Provide specific examples to demonstrate the steps**. Include copy/pasteable snippets which you use in those examples, as [Markdown code blocks](https://help.github.com/articles/markdown-basics/#multiple-lines).
* **Describe the current behavior** and **explain which behavior you expected to see instead** and why.
* **Include screenshots and animated GIFs** which help you demonstrate the steps or point out the part of GramAddict which the suggestion is related to. You can use [this tool](https://www.cockos.com/licecap/) to record GIFs on macOS and Windows, and [this tool](https://github.com/colinkeenan/silentcast) or [this tool](https://github.com/GNOME/byzanz) on Linux.
* **Explain why this enhancement would be useful** to most GramAddict users.
* **Specify which version of GramAddict you're using.** You can get the exact version by checking the log when you run the script.
* **Specify the name and version of the OS you're using.**
* **Specify the model of phone/tablet or name and version number of the emulator you are using.**
* **Specify the version of Instagram you are running.**



### Your First Code Contribution

Unsure where to begin contributing to GramAddict? You can start by looking for `beginner` and `help-wanted` issues:

* [Beginner issues][beginner] - issues which should only require a few lines of code, and a test or two.
* [Help wanted issues][help-wanted] - issues which should be a bit more involved than `beginner` issues.

Both issue lists are sorted by total number of comments. While not perfect, number of comments is a reasonable proxy for impact a given change will have.

If you want to read about using GramAddict or developing packages in GramAddict, the [GramAddict Docs](https://doc.gramaddict.org) are available to assist with every aspect of GramAddict.


### Making Changes

* Create a topic branch from where you want to base your work.
  * This is almost always the develop branch.
  * To quickly create a topic branch based on develop, run `git checkout -b
    feature-mybranch develop`. Please avoid working directly on the
    `develop` branch.
* Make commits using the [styleguides](#styleguides)
* Make sure to [Blacken](https://github.com/psf/black) your code before committing
* Make sure your commit messages are in the proper format. If the commit addresses an issue filed in the GitHub, end the first line of the commit with the issue number prefaced by a #.

Example:
  ```
      :cat2: Fixing an encoding bug with the logging system #31

      - Without utf-8 encoding, certain logs cannot be written and will cause an exception
  ```

### Pull Requests

The process described here has several goals:

- Maintain GramAddict's quality
- Fix problems that are important to users
- Engage the community in working toward the best possible GramAddict
- Enable a sustainable system for GramAddict's maintainers to review contributions

Please follow these steps to have your contribution considered by the maintainers:

1. Follow all instructions in [the template](.github/PULL_REQUEST_TEMPLATE.md)
2. Follow the [styleguides](#styleguides)
3. After you submit your pull request, verify that all [status checks](https://help.github.com/articles/about-status-checks/) are passing <details><summary>What if the status checks are failing?</summary>If a status check is failing, and you believe that the failure is unrelated to your change, please leave a comment on the pull request explaining why you believe the failure is unrelated. A maintainer will re-run the status check for you. If we conclude that the failure was a false positive, then we will open an issue to track that problem with our status check suite.</details>

While the prerequisites above must be satisfied prior to having your pull request reviewed, the reviewer(s) may ask you to complete additional design work, tests, or other changes before your pull request can be ultimately accepted.

<br />

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Consider starting the commit message with an applicable emoji:
    * :cat2: `:cat2:` when fixing or improving existing code
    * :racehorse: `:racehorse:` when improving performance
    * :memo: `:memo:` when writing docs
    * :penguin: `:penguin:` when fixing something on Linux
    * :apple: `:apple:` when fixing something on macOS
    * :checkered_flag: `:checkered_flag:` when fixing something on Windows
    * :bug: `:bug:` when fixing a bug
    * :fire: `:fire:` when removing code or files
    * :green_heart: `:green_heart:` when fixing the CI build
    * :white_check_mark: `:white_check_mark:` when adding tests
    * :lock: `:lock:` when dealing with security
    * :arrow_up: `:arrow_up:` when upgrading dependencies
    * :arrow_down: `:arrow_down:` when downgrading dependencies
    * :gift: `:gift:` when adding a new feature
    * :rage: `:rage:` when fixing something the linter complained about

### Python Styleguide

All Python code is linted with [Black](https://github.com/psf/black) using the default settings. Your code will not be accepted if it is not blackened.
