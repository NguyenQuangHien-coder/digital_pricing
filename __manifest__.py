# -*- coding: utf-8 -*-

{
    'name': 'License Management',
    'summary': """VUA HE THONG - License Management""",
    'description': """
        VUA HE THONG - License Management
    """,
    'author': 'VUA HE THONG',
    'website': 'https://www.vuahethong.com',
    'category': 'License Management/License Management',
    'version': '14.0.1.0.0',
    'depends': [
        'sale_subscription',
        'stock',
        'product',
        'website',
        'website_sale',
        'l10n_vn',
    ],
    'qweb': [

    ],
    'data': [
        'data/pricing_data.xml',
        'data/product_variants_sequence.xml',
        'security/ir.model.access.csv',
        'wizard/sale_subscription_wizard_views.xml',
        'wizard/sale_subscription_wizard_delete_server_views.xml',
        'wizard/sale_subscription_wizard_redeploy_server_views.xml',
        # 'wizard/sale_make_invoice_advance_views.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/sale_subscription_views.xml',
        'views/subscription_portal_templates.xml',
        'views/product_views.xml',
        'views/product_template_views.xml',
        'views/pricing_templates.xml',
        'views/cart_lines_template.xml',
        'views/sale_views.xml',
        'views/website_sale__templates.xml',
        'views/portal_templates.xml',
        # 'views/sale_portal_templates.xml',
        'views/product_digital_package_views.xml',
        # 'views/account_move_views.xml',
        'views/report_invoice.xml',
       
    ],
    'license': 'LGPL-3',
    'installable': True,
}