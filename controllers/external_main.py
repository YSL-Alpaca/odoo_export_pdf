# -*- coding: utf-8 -*-

from odoo import http
import base64
import copy
import datetime
import functools
import hashlib
import io
import itertools
import json
import logging
import operator
import os
import re
import sys
import tempfile
import unicodedata
from collections import OrderedDict, defaultdict

import babel.messages.pofile
import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from lxml import etree, html
from markupsafe import Markup
from werkzeug.urls import url_encode, url_decode, iri_to_uri

import odoo
import odoo.modules.registry
from odoo.api import call_kw
from odoo.addons.base.models.ir_qweb import render as qweb_render
from odoo.modules import get_resource_path, module
from odoo.tools import html_escape, pycompat, ustr, apply_inheritance_specs, lazy_property, float_repr, osutil
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.translate import _
from odoo.tools.misc import str2bool, xlsxwriter, file_open, file_path
from odoo.tools.safe_eval import safe_eval, time
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.models import check_method_name
from odoo.service import db, security
from odoo.http import serialize_exception as _serialize_exception
from odoo.tools.misc import str2bool, xlsxwriter, file_open, file_path
from odoo.addons.web.controllers.main import Export, ExportFormat, ExcelExport, serialize_exception, GroupsTreeNode
import pandas as pd
from openpyxl import load_workbook
from .css_str import styled_html

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PDF_PATH = BASE_DIR + "/static/src/export_pdf.pdf"
EXCEL_PATH = BASE_DIR + '/static/src/export_excel.xlsx'


class ExportExt(Export):

    @http.route('/web/export/formats', type='json', auth="user")
    def formats(self):
        """ Returns all valid export formats

        :returns: for each export format, a pair of identifier and printable name
        :rtype: [(str, str)]
        """
        return [
            {'tag': 'xlsx', 'label': 'XLSX', 'error': None if xlsxwriter else "XlsxWriter 0.9.3 required"},
            {'tag': 'csv', 'label': 'CSV'},
            {'tag': 'pdf', 'label': 'PDF'},
        ]


class PDFExport(ExcelExport, http.Controller):

    def base_ext(self, data):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        Model = request.env[model].with_context(**params.get('context', {}))
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby, lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree)
        else:
            Model = Model.with_context(import_compat=import_compat)
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas',[])
            response_data = self.from_data(columns_headers, export_data)
        # 写入模板文件
        with open(EXCEL_PATH, 'wb') as file:
            file.write(response_data)
        return model

    @staticmethod
    def excel_to_html():
        """
        excel文件转html字符串,并拼接css字符串
        :return: html字符串
        """
        # 读取Excel文件
        excel_file = pd.ExcelFile(EXCEL_PATH)
        df = excel_file.parse('Sheet1')
        html_table = df.to_html(index=False)
        html_str = styled_html.format(html_table=html_table)
        # 引入html转pdf库,放到此处,防止环境问题,导致引入失败无法启动odoo服务
        # from weasyprint import HTML
        # """HTML 2 PDF"""
        # HTML(string=styled_html).write_pdf(PDF_PATH)
        import pdfkit
        pdfkit.from_string(html_str, PDF_PATH)

    @http.route('/web/export/pdf', type='http', auth="user")
    @serialize_exception
    def pdf_export(self, data):
        model = self.base_ext(data)
        # excel转html
        self.excel_to_html()
        with open(PDF_PATH, 'rb') as file:
            response_data = file.read()
        # # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(response_data,
                                     headers=[('Content-Disposition',
                                               content_disposition(
                                                   osutil.clean_filename(self.filename(model) + self.extension_ext))),
                                              ('Content-Type', self.content_type)],
                                     )

    @property
    def extension_ext(self):
        return '.pdf'


