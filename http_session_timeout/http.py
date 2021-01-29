# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution, third party addon
#    Copyright (C) 2020 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import time
import random
import odoo.http
from odoo.tools import config
 
def session_gc(session_store):
    if random.random() < 0.001:
        # session timeout can be set by config, default 16h
        last_week = time.time() - int(config.get('session_timeout', 60*60*16))
        for fname in os.listdir(session_store.path):
            path = os.path.join(session_store.path, fname)
            try:
                if os.path.getmtime(path) < last_week:
                    os.unlink(path)
            except OSError:
                pass

# Monkey patching our function into core.
odoo.http.session_gc = session_gc
