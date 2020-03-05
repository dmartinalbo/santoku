#!/bin/bash

VERSION_NUMBER=$1
RELEASE_TYPE=$2

if [ "$RELEASE_TYPE" == "M" ]; then
	# increase (M)ajor part
	echo ${VERSION_NUMBER} | awk -F'.' '{printf "%d.%d",$1+1,$2}'
else
	# increase (m)inor part
	echo ${VERSION_NUMBER} | awk -F'.' '{printf "%d.%d",$1,$2+1}'
fi
