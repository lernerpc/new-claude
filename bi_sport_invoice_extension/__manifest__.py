{
    'name': "Sports Center Invoice Extension",
    'version': '1.0.0',
    'summary': "Extends invoice creation to include multiple invoices based on membership fees and integrates pricelist pricing.",
    'depends': ['bi_sport_center_management', 'bi_sport_membership_fees', 'account', 'product', 'bi_sport_pricelist_extension'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'data/fix_invoice_links.xml',  # Commented out for now
    ],
    'demo': [],  # Empty or remove this line completely

    'installable': True,
    'auto_install': False,
    'application': False,
}
