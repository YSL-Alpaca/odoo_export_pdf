{
    'name': "odoo_export_pdf",

    'summary': """
        odoo export pdf""",
    'description': """
        
    """,

    'author': "silu.yang",

    'category': 'apps',
    'version': '1.0',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'web'],
    'application': True,

    # always loaded
    'data': [
    ],
    'assets': {
        'web.assets_qweb': [
        ],
        'web.assets_backend': [
        ],
    },
    'qweb': ['static/xml/*.xml'],
}
# -*- coding: utf-8 -*-
