#!/bin/bash
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

usage="$(basename "$0") [-h] [-m MODULE] [-a] [-p] -- runs syntax check with
the checkbashisms tool. By default checks only changed and unstaged files.

where:
    -h|--help             show this help text
    -a|--all              check all files in the CHECK_PATH (default ./ocf) dir
    -p|--POSIX            run POSIX:2001 checks against bash shebangs as well
"

CHECK_PATH="${CHECK_PATH:-./ocf}"
POSIX_CHECKS=1
ALL=1
while [ $# -gt 0 ] ; do
    key="$1"

    case $key in
        -h|--help)
            echo "$usage" >&2
            exit 0
        ;;
        -a|--all)
            ALL=0
        ;;
        -p|--POSIX)
            POSIX_CHECKS=0
        ;;
        *)
        ;;
    esac
    shift
done

TMPFILE=$(mktemp /tmp/tmp.XXXXXXXXXX)
# Register exit trap for removing temporary files
trap 'rm -rf $TMPFILE' EXIT INT HUP

# Function for check shell scripts
check_bash() {
    local rc
    bash -n "$1"
    rc=$?
    [ $rc -ne 0 ] && return $rc

    if [ $POSIX_CHECKS -eq 0 ]; then
        cat "$1" > "${TMPFILE}"
        sed -i -e 's%^#!/bin/bash%#!/bin/sh%g' "${TMPFILE}" >/dev/null 2>&1
        /usr/bin/checkbashisms "${TMPFILE}"
        rc=$?
    else
        /usr/bin/checkbashisms "$1"
        rc=$?
    fi
    [ $rc -eq 4 ] && rc=0
    return $rc
}

# Function that checks syntax
check_syntax() {
    local rc
    local exit_code
    local all_files
    local failed_files
    local x
    exit_code=0
    if [ $ALL -eq 0 ]; then
        all_files="$(find ${CHECK_PATH} -type f -o -type f -path ${CHECK_PATH})"
    else
        # Get a list of files changed in this transaction
        all_files="$(git diff --name-only HEAD)"
    fi
    for x in $all_files; do
        case $(file --mime --brief $x) in
            *x-shellscript*)
                check_bash "${x}"
                rc=$?
                if [ $rc -ne 0 ] ; then
                    exit_code=1
                    failed_files=$(printf "%b\n" "${failed_files}" "${x}")
                fi
            ;;
        esac
    done
    echo "${failed_files}"
    return $exit_code
}

if results=$(check_syntax); then
    echo "Syntax Test SUCCEEDED: no syntax errors found"
    exit 0
else
    echo "Syntax Test FAILED: syntax errors found in the following files:"
    printf "%b\n" "${results}"
    exit 1
fi
