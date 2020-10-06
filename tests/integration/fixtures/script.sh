#!/bin/bash
# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


# Example of a Command trigger

echo "Test demonstrating a Command trigger"
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -d|--date)
    DATE="$2"
    shift # past argument
    shift # past value
    ;;
    -s|--stream)
    STREAM="$2"
    shift # past argument
    shift # past value
    ;;
    -j|--json)
    JSON="$2"
    shift # past argument
    shift # past value
    ;;
    -p|--jsonpath)
    JSONPATH="$2"
    shift # past argument
    shift # past value
    ;;
esac
done

echo Notification received for stream $STREAM on date: $DATE
echo at $TIME step: $STEP
echo json: $JSON
echo jsonpath: $JSONPATH
echo "Script executed successfully"