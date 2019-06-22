# =================================================================
#
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#
# Copyright (c) 2019 Tom Kralidis
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import logging

import tinydb
from tinyrecord import transaction

from pygeoapi.process.manager.base import BaseManager

LOGGER = logging.getLogger(__name__)


class TinyDBManager(BaseManager):
    """TinyDB Manager"""

    def __init__(self, manager_def):
        """
        Initialize object

        :param manager_def: manager definition

        :returns: `pygeoapi.process.manager.base.BaseManager`
        """

        BaseManager.__init__(self, manager_def)

        self.name = manager_def['name']
        self.connection = manager_def['connection']

    def create(self):
        """
        Create manager

        :returns: `bool` of status of result
        """

        self.db = tinydb.TinyDB(self.connection)
        return True

    def destroy(self):
        """
        Destroy manager

        :returns: `bool` status of result
        """

        self.db.purge()
        return True

    def get_jobs(self, processid=None, status=None):
        """
        Get jobs

        :param processid: process identifier
        :param status: job status (accepted, running, successful,
                       failed, results) (default is all)

        :returns: 'list` of jobs (identifier, status, process identifier)
        """

        if processid is None:
            return [doc.doc_id for doc in self.db.all()]
        else:
            query = tinydb.Query()
            return self.db.search(query.processid == processid)

        raise NotImplementedError()

    def add_job(self, job_metadata):
        """
        Add a job

        :param job_metadata: `dict` of job metadata

        :returns: `bool` of add job result
        """

        with transaction(self.db) as tr:
            doc_id = tr.insert(job_metadata)
        return doc_id

    def delete_jobs(self, max_jobs, older_than):
        """
        TODO
        """
        raise NotImplementedError()

    def get_job_result(self, processid, jobid):
        """
        Get a single job

        :param processid: process identifier
        :param jobid: job identifier

        :returns: `dict`  # `pygeoapi.process.manager.Job`
        """

        query = tinydb.Query()
        r = self.db.search(query.processid == processid, query.jobid == jobid)

        return r

    def add_job_result(self, processid, jobid):
        """
        Add a job result

        :param processid: process identifier
        :param jobid: job identifier

        :returns: `bool` of add job result result
        """

    def __repr__(self):
        return '<TinyDBManager> {}'.format(self.name)


class ManagerExecuteError(Exception):
    """query / backend error"""
    pass