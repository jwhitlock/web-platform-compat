============
Contributing
============

Contributions should follow the `MDN Contribution Guidelines`_:

* You agree to license your contributions under `MPL 2`_
* Discuss large changes on the `dev-mdn mailing list`_ or on a `bugzilla bug`_
  before coding.
* Python code style should follow `PEP8 standards`_ whenever possible.
* All commit messages must start with "bug NNNNNNN" or "fix bug NNNNNNN"
    * Reason: Make it easy for someone to consume the commit log and reach
      originating requests for all changes
    * Exceptions: "Merge" and "Revert" commits
    * Notes:
        * "fix bug NNNNNNN" - will trigger a github bot to automatically mark
          bug as "RESOLVED:FIXED"
        * If a pull request has multiple commits, we should squash commits
          together or re-word commit messages so that each commit message
          contains a bug number
* MDN module `owner or peer`_ must review and merge all pull requests.
    * Reason: Owner and peers are and accountable for the quality of MDN code
      changes
    * Exceptions: Owners/peers may commit directly to master for critical
      security/down-time fixes; they must file a bug for follow-up review.
* MDN reviewers must verify sufficient test coverage on all changes - either by new or existing tests.
    * Reason: Automated tests reduce human error involved in reviews
    * Notes: The Django site has `good testing docs`_, and
      `Django REST framework`_ has some `additonal testing docs`_.

.. _`MDN Contribution Guidelines`: https://github.com/mozilla/kuma/blob/master/CONTRIBUTING.md
.. _`MPL 2`: http://www.mozilla.org/MPL/2.0/
.. _`dev-mdn mailing list`: https://lists.mozilla.org/listinfo/dev-mdn
.. _`bugzilla bug`: https://bugzilla.mozilla.org/show_bug.cgi?id=989448
.. _`PEP8 standards`: http://www.python.org/dev/peps/pep-0008/
.. _`owner or peer`: https://wiki.mozilla.org/Modules/All#MDN
.. _`good testing docs`: https://docs.djangoproject.com/en/dev/topics/testing/
.. _`Django REST framework`: http://www.django-rest-framework.org
.. _`additonal testing docs`: http://www.django-rest-framework.org/api-guide/testing

What to work on
---------------
There is a `tracking bug`_ for this project, and a `specific bug`_ for the data
store, the primary purpose of this project.  The dependant bugs represent
areas of work, and are not exhaustive.  If you want to contribute at this phase
in development, take a look at the bugs and linked documents, to familiarize
yourself with the project, and then get in touch with the team on IRC (#mdndev
on irc.mozilla.org) to carve out a piece of the project.

.. _`tracking bug`: https://bugzilla.mozilla.org/showdependencytree.cgi?id=989448&hide_resolved=1
.. _`specific bug`: https://bugzilla.mozilla.org/showdependencytree.cgi?id=996570&hide_resolved=1

GitHub workflow
---------------
1. `Get your environment setup`_
2. Set up mozilla remote
   (``$ git remote add mozilla git://github.com/mdn/browsercompat.git``)
3. Create a branch for a bug
   (``$ git checkout -b new-issue-888888``)
4. Develop on bug branch.

   `Time passes, the mdn/browsercompat repository accumulates new commits`
5. Commit changes to bug branch 
   (``$ git add . ; git commit -m 'fix bug 888888 - commit message'``)
6. Fetch mozilla
   (``$ git fetch mozilla``)
7. Update local master
   (``$ git checkout master; git pull mozilla master``)

   `Repeat steps 4-7 till dev is complete`

8. Rebase issue branch
   (``$ git checkout new-issue-888888; git rebase master``)
9. Push branch to GitHub
   (``$ git push origin new-issue-888888``)
10. Issue pull request (Click Pull Request button)

.. _`Get your environment setup`: https://github.com/mdn/browsercompat/wiki/Installation
