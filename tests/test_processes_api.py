# =================================================================
#
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#          John A Stevenson <jostev@bgs.ac.uk>
#          Colin Blackburn <colb@bgs.ac.uk>
#
# Copyright (c) 2023 Tom Kralidis
# Copyright (c) 2022 John A Stevenson and Colin Blackburn
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

import json
import logging
import time
from http import HTTPStatus


from pygeoapi.api import API
from pygeoapi.api.processes import execute_process

from .util import mock_api_request, mock_request


LOGGER = logging.getLogger(__name__)


def test_execute_process(api_: API):
    req_body_0 = {
        'inputs': {
            'name': 'Test'
        }
    }
    req_body_1 = {
        'inputs': {
            'name': 'Test'
        },
        'response': 'document'
    }
    req_body_2 = {
        'inputs': {
            'name': 'Tést'
        }
    }
    req_body_3 = {
        'inputs': {
            'name': 'Tést',
            'message': 'This is a test.'
        }
    }
    req_body_4 = {
        'inputs': {
            'foo': 'Tést'
        }
    }
    req_body_5 = {
        'inputs': {}
    }
    req_body_6 = {
        'inputs': {
            'name': None
        }
    }

    cleanup_jobs = set()

    # Test posting empty payload to existing process
    req = mock_api_request(data='')
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')  # noqa
    assert rsp_headers['Content-Language'] == 'en-US'

    data = json.loads(response)
    assert code == HTTPStatus.BAD_REQUEST
    assert 'Location' not in rsp_headers
    assert data['code'] == 'MissingParameterValue'

    req = mock_api_request(data=req_body_0)
    rsp_headers, code, response = execute_process(api_, req, 'foo')  # noqa

    data = json.loads(response)
    assert code == HTTPStatus.NOT_FOUND
    assert 'Location' not in rsp_headers
    assert data['code'] == 'NoSuchProcess'

    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    data = json.loads(response)
    assert code == HTTPStatus.OK
    assert 'Location' in rsp_headers

    assert len(data.keys()) == 2
    assert data['id'] == 'echo'
    assert data['value'] == 'Hello Test!'

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_1)
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    data = json.loads(response)
    assert code == HTTPStatus.OK
    assert 'Location' in rsp_headers

    assert len(data.keys()) == 1
    assert data['outputs'][0]['id'] == 'echo'
    assert data['outputs'][0]['value'] == 'Hello Test!'

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_2)
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    data = json.loads(response)
    assert code == HTTPStatus.OK
    assert 'Location' in rsp_headers
    assert data['value'] == 'Hello Tést!'

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_3)
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    data = json.loads(response)
    assert code == HTTPStatus.OK
    assert 'Location' in rsp_headers
    assert data['value'] == 'Hello Tést! This is a test.'

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_4)
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    data = json.loads(response)
    assert code == HTTPStatus.OK
    assert 'Location' in rsp_headers
    assert data['code'] == 'InvalidParameterValue'
    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_5)
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')
    data = json.loads(response)
    assert code == HTTPStatus.OK
    assert 'Location' in rsp_headers
    assert data['code'] == 'InvalidParameterValue'
    assert data['description'] == 'Error updating job'

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_6)
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    data = json.loads(response)
    assert code == HTTPStatus.OK
    assert 'Location' in rsp_headers
    assert data['code'] == 'InvalidParameterValue'
    assert data['description'] == 'Error updating job'

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_0)
    rsp_headers, code, response = execute_process(api_, req, 'goodbye-world')

    response = json.loads(response)
    assert code == HTTPStatus.NOT_FOUND
    assert 'Location' not in rsp_headers
    assert response['code'] == 'NoSuchProcess'

    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    response = json.loads(response)
    assert code == HTTPStatus.OK

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    req = mock_api_request(data=req_body_1, HTTP_Prefer='respond-async')
    rsp_headers, code, response = execute_process(api_, req, 'hello-world')

    assert 'Location' in rsp_headers
    response = json.loads(response)
    assert isinstance(response, dict)
    assert code == HTTPStatus.CREATED

    cleanup_jobs.add(tuple(['hello-world',
                            rsp_headers['Location'].split('/')[-1]]))

    # Cleanup
    time.sleep(2)  # Allow time for any outstanding async jobs
    for _, job_id in cleanup_jobs:
        rsp_headers, code, response = api_.delete_job(mock_request(), job_id)
        assert code == HTTPStatus.OK
