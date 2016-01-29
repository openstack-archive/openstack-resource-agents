#!/usr/bin/make -f
#
# Makefile for the OpenStack resource agents toolsuite
#
# Copyright (C) 2012 hastexo Professional Services GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language
# governing permissions and limitations under the License.

# define some common variables
INSTALL = /usr/bin/install

default:

install:
	mkdir -p $(DESTDIR)/usr/lib/ocf/resource.d/openstack
	for file in ocf/*; do \
		$(INSTALL) -t $(DESTDIR)/usr/lib/ocf/resource.d/openstack -m 0755 $${file} ; \
	done

syntax-check:
	utils/syntax_check.sh -a -p
