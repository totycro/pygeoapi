# =================================================================
#
# Authors: Tom Kralidis <tomkralidis@gmail.com>
#          Francesco Bartoli <xbartolone@gmail.com>
#          Sander Schaminee <sander.schaminee@geocat.net>
#          John A Stevenson <jostev@bgs.ac.uk>
#          Colin Blackburn <colb@bgs.ac.uk>
#          Ricardo Garcia Silva <ricardo.garcia.silva@geobeyond.it>
#          Bernhard Mallinger <bernhard.mallinger@eox.at>
#
# Copyright (c) 2023 Tom Kralidis
# Copyright (c) 2022 Francesco Bartoli
# Copyright (c) 2022 John A Stevenson and Colin Blackburn
# Copyright (c) 2023 Ricardo Garcia Silva
# Copyright (c) 2023 Bernhard Mallinger
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
import json
from http import HTTPStatus
from typing import Tuple

from pygeoapi.util import (
    json_serial, render_j2_template, JobStatus, RequestedProcessExecutionMode,
    to_json)
from pygeoapi.process.base import (
    JobNotFoundError,
    JobResultNotFoundError,
    ProcessorExecuteError,
)
from pygeoapi.process.manager.base import get_manager
from pygeoapi.openapi import OPENAPI_YAML

from . import APIRequest, API, SYSTEM_LOCALE, F_JSON, FORMAT_TYPES

LOGGER = logging.getLogger(__name__)


def execute_process(api: API, request: APIRequest,
                    process_id) -> Tuple[dict, int, str]:
    """
    Execute process

    :param request: A request object
    :param process_id: id of process

    :returns: tuple of headers, status code, content
    """

    # Responses are always in US English only
    headers = request.get_response_headers(SYSTEM_LOCALE,
                                           **api.api_headers)
    if process_id not in api.manager.processes:
        msg = 'identifier not found'
        return api.get_exception(
            HTTPStatus.NOT_FOUND, headers,
            request.format, 'NoSuchProcess', msg)

    data = request.data
    if not data:
        # TODO not all processes require input, e.g. time-dependent or
        #      random value generators
        msg = 'missing request data'
        return api.get_exception(
            HTTPStatus.BAD_REQUEST, headers, request.format,
            'MissingParameterValue', msg)

    try:
        # Parse bytes data, if applicable
        data = data.decode()
        LOGGER.debug(data)
    except (UnicodeDecodeError, AttributeError):
        pass

    try:
        data = json.loads(data)
    except (json.decoder.JSONDecodeError, TypeError) as err:
        # Input does not appear to be valid JSON
        LOGGER.error(err)
        msg = 'invalid request data'
        return api.get_exception(
            HTTPStatus.BAD_REQUEST, headers, request.format,
            'InvalidParameterValue', msg)

    data_dict = data.get('inputs', {})
    LOGGER.debug(data_dict)

    try:
        execution_mode = RequestedProcessExecutionMode(
            request.headers.get('Prefer', request.headers.get('prefer'))
        )
    except ValueError:
        execution_mode = None
    try:
        LOGGER.debug('Executing process')
        result = api.manager.execute_process(
            process_id, data_dict, execution_mode=execution_mode)
        job_id, mime_type, outputs, status, additional_headers = result
        headers.update(additional_headers or {})
        headers['Location'] = f'{api.base_url}/jobs/{job_id}'
    except ProcessorExecuteError as err:
        LOGGER.error(err)
        msg = 'Processing error'
        return api.get_exception(
            HTTPStatus.INTERNAL_SERVER_ERROR, headers,
            request.format, 'NoApplicableCode', msg)

    response = {}
    if status == JobStatus.failed:
        response = outputs

    if data.get('response', 'raw') == 'raw':
        headers['Content-Type'] = mime_type
        response = outputs
    elif status not in (JobStatus.failed, JobStatus.accepted):
        response['outputs'] = [outputs]

    if status == JobStatus.accepted:
        http_status = HTTPStatus.CREATED
    else:
        http_status = HTTPStatus.OK

    if mime_type == 'application/json':
        response2 = to_json(response, api.pretty_print)
    else:
        response2 = response

    return headers, http_status, response2


def get_job_result(api: API, request: APIRequest,
                   job_id) -> Tuple[dict, int, str]:
    """
    Get result of job (instance of a process)

    :param request: A request object
    :param job_id: ID of job

    :returns: tuple of headers, status code, content
    """

    headers = request.get_response_headers(SYSTEM_LOCALE,
                                           **api.api_headers)
    try:
        job = api.manager.get_job(job_id)
    except JobNotFoundError:
        return api.get_exception(
            HTTPStatus.NOT_FOUND, headers,
            request.format, 'NoSuchJob', job_id
        )

    status = JobStatus[job['status']]

    if status == JobStatus.running:
        msg = 'job still running'
        return api.get_exception(
            HTTPStatus.NOT_FOUND, headers,
            request.format, 'ResultNotReady', msg)

    elif status == JobStatus.accepted:
        # NOTE: this case is not mentioned in the specification
        msg = 'job accepted but not yet running'
        return api.get_exception(
            HTTPStatus.NOT_FOUND, headers,
            request.format, 'ResultNotReady', msg)

    elif status == JobStatus.failed:
        msg = 'job failed'
        return api.get_exception(
            HTTPStatus.BAD_REQUEST, headers, request.format,
            'InvalidParameterValue', msg)

    try:
        mimetype, job_output = api.manager.get_job_result(job_id)
    except JobResultNotFoundError:
        return api.get_exception(
            HTTPStatus.INTERNAL_SERVER_ERROR, headers,
            request.format, 'JobResultNotFound', job_id
        )

    if mimetype not in (None, FORMAT_TYPES[F_JSON]):
        headers['Content-Type'] = mimetype
        content = job_output
    else:
        if request.format == F_JSON:
            content = json.dumps(job_output, sort_keys=True, indent=4,
                                 default=json_serial)
        else:
            # HTML
            data = {
                'job': {'id': job_id},
                'result': job_output
            }
            content = render_j2_template(
                api.config, 'jobs/results/index.html',
                data, request.locale)

    return headers, HTTPStatus.OK, content


def get_oas_30_paths(cfg: dict):
    paths = {}

    process_manager = get_manager(cfg)

    if len(process_manager.processes) > 0:
        paths['/processes'] = {
            'get': {
                'summary': 'Processes',
                'description': 'Processes',
                'tags': ['server'],
                'operationId': 'getProcesses',
                'parameters': [
                    {'$ref': '#/components/parameters/f'}
                ],
                'responses': {
                    '200': {'$ref': f"{OPENAPI_YAML['oapip']}/responses/ProcessList.yaml"},  # noqa
                    'default': {'$ref': '#/components/responses/default'}
                }
            }
        }
        LOGGER.debug('setting up processes')

        for k, v in process_manager.processes.items():
            if k.startswith('_'):
                LOGGER.debug(f'Skipping hidden layer: {k}')
                continue

            paths[f"/processes/{v}"] = ...

    return paths
