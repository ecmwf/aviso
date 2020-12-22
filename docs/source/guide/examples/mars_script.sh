#!/bin/bash
# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

# Example of a Command trigger

echo "Test demonstrating a command trigger executing MARS request"
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    --date)
    DATE="$2"
    shift # past argument
    shift # past value
    ;;
    --stream)
    STREAM="$2"
    shift # past argument
    shift # past value
    ;;
    --time)
    TIME="$2"
    shift # past argument
    shift # past value
    ;;
    --step)
    STEP="$2"
    shift # past argument
    shift # past value
    ;;
esac
done

echo Notification received for stream $STREAM, date $DATE, time $TIME, step $STEP
echo Building MARS request

REQUEST="
retrieve,
class=od,
date="$DATE",
expver=1,
levtype=sfc,
param=167.128,
stream="$STREAM",
time="$TIME",
step="$STEP",
type=an,
area=75/-20/10/60,
target="my_data.grib"
"
echo Request built, sending it...
echo $REQUEST | mars
echo Script executed successfully